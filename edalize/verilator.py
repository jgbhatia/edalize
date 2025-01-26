# Copyright edalize contributors
# Licensed under the 2-Clause BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-2-Clause

import logging
import os
import logging

from edalize.edatool import Edatool

logger = logging.getLogger(__name__)

CONFIG_MK_TEMPLATE = """#Auto generated by Edalize

TOP_MODULE        := {top_module}
VC_FILE           := {vc_file}
VERILATOR_OPTIONS := {verilator_options}
MAKE_OPTIONS      := {make_options}
"""

MAKEFILE_TEMPLATE = """#Auto generated by Edalize

include config.mk

#Assume a local installation if VERILATOR_ROOT is set
ifeq ($(VERILATOR_ROOT),)
VERILATOR ?= verilator
else
VERILATOR ?= $(VERILATOR_ROOT)/bin/verilator
endif

V$(TOP_MODULE): V$(TOP_MODULE).mk
	$(MAKE) $(MAKE_OPTIONS) -f $<
V$(TOP_MODULE).mk:
	$(EDALIZE_LAUNCHER) $(VERILATOR) -f $(VC_FILE) $(VERILATOR_OPTIONS)

.PHONY: binary dpi-hdr-only lint-only preprocess-only xml-only
binary:
	$(EDALIZE_LAUNCHER) $(VERILATOR) --binary -f $(VC_FILE) $(VERILATOR_OPTIONS)
dpi-hdr-only:
	$(EDALIZE_LAUNCHER) $(VERILATOR) --dpi-hdr-only -f $(VC_FILE) $(VERILATOR_OPTIONS)
lint-only:
	$(EDALIZE_LAUNCHER) $(VERILATOR) --lint-only -f $(VC_FILE) $(VERILATOR_OPTIONS)
preprocess-only V$(TOP_MODULE).i:
	$(EDALIZE_LAUNCHER) $(VERILATOR) -E -f $(VC_FILE) $(VERILATOR_OPTIONS) > V$(TOP_MODULE).i
xml-only V$(TOP_MODULE).xml:
	$(EDALIZE_LAUNCHER) $(VERILATOR) --xml-only -f $(VC_FILE) $(VERILATOR_OPTIONS)
"""


class Verilator(Edatool):
    argtypes = ["cmdlinearg", "plusarg", "vlogdefine", "vlogparam"]

    modes = [
        "binary",
        "cc",
        "dpi-hdr-only",
        "lint-only",
        "none",
        "preprocess-only",
        "sc",
        "xml-only",
    ]

    @classmethod
    def get_doc(cls, api_ver):
        if api_ver == 0:
            return {
                "description": "Verilator is the fastest free Verilog HDL simulator, and outperforms most commercial simulators",
                "members": [
                    {
                        "name": "mode",
                        "type": "String",
                        "desc": "Select compilation mode. Legal values are *binary*, *cc*, *dpi-hdr-only*, *lint-only*, *none*, *preprocess-only*, *sc*, *xml-only*. See Verilator documentation for function: https://veripool.org/guide/latest/exe_verilator.html",
                    },
                    {
                        "name": "cli_parser",
                        "type": "String",
                        "desc": "**Deprecated: Use run_options instead** : Select whether FuseSoC should handle command-line arguments (*managed*) or if they should be passed directly to the verilated model (*raw*). Default is *managed*",
                    },
                    {
                        "name": "exe",
                        "type": "String",
                        "desc": "Controls whether to create an executable. Set to 'false' when something else will do the final linking",
                    },
                    {
                        "name": "gen-xml",
                        "type": "bool",
                        "desc": "Generate XML output",
                    },
                    {
                        "name": "gen-dpi-hdr",
                        "type": "bool",
                        "desc": "Generate DPI header output",
                    },
                    {
                        "name": "gen-preprocess",
                        "type": "bool",
                        "desc": "Generate preprocessor output",
                    },
                ],
                "lists": [
                    {
                        "name": "libs",
                        "type": "String",
                        "desc": "Extra libraries for the verilated model to link against",
                    },
                    {
                        "name": "verilator_options",
                        "type": "String",
                        "desc": "Additional options for verilator",
                    },
                    {
                        "name": "make_options",
                        "type": "String",
                        "desc": "Additional arguments passed to make when compiling the simulation. This is commonly used to set OPT/OPT_FAST/OPT_SLOW.",
                    },
                    {
                        "name": "run_options",
                        "type": "String",
                        "desc": "Additional arguments directly passed to the verilated model",
                    },
                ],
            }

    def check_managed_parser(self):
        managed = (
            "cli_parser" not in self.tool_options
            or self.tool_options["cli_parser"] == "managed"
        )
        if not managed:
            logger.warning(
                "The cli_parser argument is deprecated. Use run_options to pass raw arguments to verilated models"
            )

    def configure_main(self):
        logger.warning(
            "This backend is deprecated and will eventually be removed. Please migrate to the flow API instead.  See https://edalize.readthedocs.io/en/latest/ref/migrations.html#migrating-from-the-tool-api-to-the-flow-api for more details."
        )
        self.check_managed_parser()
        if not self.toplevel:
            raise RuntimeError(
                "'" + self.name + "' miss a mandatory parameter 'top_module'"
            )

        self._write_config_files()

    def _write_config_files(self):
        # Future improvement: Separate include directories of c and verilog files
        incdirs = set()
        src_files = []

        (src_files, incdirs) = self._get_fileset_files(force_slash=True)

        self.verilator_file = self.name + ".vc"

        with open(os.path.join(self.work_root, self.verilator_file), "w") as f:
            f.write("--Mdir .\n")

            # Default to cc mode if not specified
            if "mode" not in self.tool_options:
                self.tool_options["mode"] = "cc"

            if self.tool_options["mode"] not in Verilator.modes:
                _s = "Illegal verilator mode {}. Allowed values are {}"
                raise RuntimeError(
                    _s.format(self.tool_options["mode"], ", ".join(Verilator.modes))
                )
            if self.tool_options["mode"] in ["cc", "sc"]:
                f.write("--" + self.tool_options["mode"] + "\n")
            if "libs" in self.tool_options:
                for lib in self.tool_options["libs"]:
                    f.write("-LDFLAGS {}\n".format(lib))
            for include_dir in incdirs:
                f.write("+incdir+" + include_dir + "\n")
                f.write("-CFLAGS -I{}\n".format(include_dir))
            vlt_files = []
            vlog_files = []
            opt_c_files = []
            for src_file in src_files:
                if src_file.file_type.startswith(
                    "systemVerilogSource"
                ) or src_file.file_type.startswith("verilogSource"):
                    vlog_files.append(src_file.name)
                elif src_file.file_type in ["cppSource", "systemCSource", "cSource"]:
                    opt_c_files.append(src_file.name)
                elif src_file.file_type == "vlt":
                    vlt_files.append(src_file.name)
                elif src_file.file_type == "user":
                    pass

            if vlt_files:
                f.write("\n".join(vlt_files) + "\n")
            f.write("\n".join(vlog_files) + "\n")
            f.write("--top-module {}\n".format(self.toplevel))
            if str(self.tool_options.get("exe")).lower() != "false":
                f.write("--exe\n")
            f.write("\n".join(opt_c_files))
            f.write("\n")
            f.write(
                "".join(
                    [
                        "-G{}={}\n".format(
                            key, self._param_value_str(value, str_quote_style='\\"')
                        )
                        for key, value in self.vlogparam.items()
                    ]
                )
            )
            f.write(
                "".join(
                    [
                        "-D{}={}\n".format(key, self._param_value_str(value))
                        for key, value in self.vlogdefine.items()
                    ]
                )
            )

        with open(os.path.join(self.work_root, "Makefile"), "w") as makefile:
            makefile.write(MAKEFILE_TEMPLATE)

        if "verilator_options" in self.tool_options:
            verilator_options = " ".join(self.tool_options["verilator_options"])
        else:
            verilator_options = ""

        if "make_options" in self.tool_options:
            make_options = " ".join(self.tool_options["make_options"])
        else:
            make_options = ""

        with open(os.path.join(self.work_root, "config.mk"), "w") as config_mk:
            config_mk.write(
                CONFIG_MK_TEMPLATE.format(
                    top_module=self.toplevel,
                    vc_file=self.verilator_file,
                    verilator_options=verilator_options,
                    make_options=make_options,
                )
            )

    def build_main(self):
        logger.info("Building simulation model")
        if "mode" not in self.tool_options:
            self.tool_options["mode"] = "cc"
        args = []

        if self.tool_options["mode"] not in Verilator.modes:
            _s = "Illegal verilator mode {}. Allowed values are {}"
            raise RuntimeError(
                _s.format(self.tool_options["mode"], ", ".join(Verilator.modes))
            )

        # PHONY Makefile targets
        if self.tool_options["mode"] in [
            "binary",
            "dpi-hdr-only",
            "lint-only",
            "preprocess-only",
            "xml-only",
        ]:
            args.append(self.tool_options["mode"])

        # Build mode
        if self.tool_options["mode"] != "none":
            self._run_tool("make", args, quiet=True)

        # Additional builds
        if str(self.tool_options.get("gen-xml")).lower() == "true":
            self._run_tool("make", ["xml-only"], quiet=True)
        if str(self.tool_options.get("gen-dpi-hdr")).lower() == "true":
            self._run_tool("make", ["dpi-hdr-only"], quiet=True)
        if str(self.tool_options.get("gen-preprocess")).lower() == "true":
            self._run_tool("make", ["preprocess-only"], quiet=True)

    def run_main(self):
        self.check_managed_parser()
        self.args = []
        for key, value in self.plusarg.items():
            self.args += ["+{}={}".format(key, self._param_value_str(value))]
        for key, value in self.cmdlinearg.items():
            self.args += ["--{}={}".format(key, self._param_value_str(value))]

        self.args += self.tool_options.get("run_options", [])

        # Default to cc mode if not specified
        if "mode" not in self.tool_options:
            self.tool_options["mode"] = "cc"
        if self.tool_options["mode"] in [
            "dpi-hdr-only",
            "lint-only",
            "preprocess-only",
            "xml-only",
        ]:
            return
        logger.info("Running simulation")
        self._run_tool("./V" + self.toplevel, self.args)
