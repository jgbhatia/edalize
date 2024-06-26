# Copyright edalize contributors
# Licensed under the 2-Clause BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-2-Clause

import logging
import os.path

from edalize.edatool import Edatool
from edalize.utils import get_file_type

logger = logging.getLogger(__name__)


class Radiant(Edatool):
    argtypes = ["generic", "vlogdefine", "vlogparam"]

    @classmethod
    def get_doc(cls, api_ver):
        if api_ver == 0:
            return {
                "description": "Backend for Lattice Radiant",
                "members": [
                    {
                        "name": "part",
                        "type": "String",
                        "desc": "FPGA part number (e.g. LIFCL-40-9BG400C)",
                    },
                ],
            }

    def configure_main(self):
        (src_files, incdirs) = self._get_fileset_files()
        pdc_file = None
        prj_name = self.name.replace(".", "_")
        for f in src_files:
            if f.file_type == "PDC":
                if pdc_file:
                    logger.warning(
                        "Multiple PDC files detected. Only the first one will be used"
                    )
                else:
                    pdc_file = f.name

        with open(os.path.join(self.work_root, self.name + ".tcl"), "w") as f:
            TCL_TEMPLATE = """#Generated by Edalize
prj_create -name {} -impl "impl" -dev {}
prj_set_impl_opt top {}
"""
            f.write(
                TCL_TEMPLATE.format(
                    prj_name,
                    self.tool_options["part"],
                    self.toplevel,
                )
            )
            if incdirs:
                _s = "prj_set_impl_opt {include path} {"
                _s += " ".join(incdirs)
                f.write(_s + "}\n")
            if self.generic:  # ?
                _s = ";".join(["{}={}".format(k, v) for k, v in self.generic.items()])
                f.write("prj_set_impl_opt HDL_PARAM {")
                f.write(_s)
                f.write("}\n")
            if self.vlogparam:
                _s = ";".join(
                    [
                        "{}={}".format(k, self._param_value_str(v, '"'))
                        for k, v in self.vlogparam.items()
                    ]
                )
                f.write("prj_set_impl_opt HDL_PARAM {")
                f.write(_s)
                f.write("}\n")
            if self.vlogdefine:
                _s = ";".join(
                    ["{}={}".format(k, v) for k, v in self.vlogdefine.items()]
                )
                f.write("prj_set_impl_opt VERILOG_DIRECTIVES {")
                f.write(_s)
                f.write("}\n")
            for src_file in src_files:
                _s = self.src_file_filter(src_file)
                if _s:
                    f.write(_s + "\n")
            f.write("prj_save\nprj_close\n")

        with open(os.path.join(self.work_root, self.name + "_run.tcl"), "w") as f:
            f.write(
                """#Generated by Edalize
prj_open {}.rdf
prj_run Synthesis -impl impl -forceOne
prj_run Map -impl impl
prj_run PAR -impl impl
prj_run Export -impl impl -task Bitgen
prj_save
prj_close
""".format(
                    prj_name
                )
            )

    def src_file_filter(self, f):
        def _work_source(f):
            s = " -work "
            if f.logical_name:
                s += f.logical_name
            else:
                s += "work"
            return s

        file_types = {
            "verilogSource": "prj_add_source ",
            "systemVerilogSource": "prj_add_source ",
            "vhdlSource": "prj_add_source ",
            "PDC": "prj_add_source ",
            "SDC": "prj_add_source ",
        }
        _file_type = get_file_type(f)
        if _file_type in file_types:
            return file_types[_file_type] + f.name + _work_source(f)
        elif _file_type == "tclSource":
            return "source " + f.name
        elif _file_type in ["user", "LPF"]:
            return ""
        else:
            _s = "{} has unknown file type '{}'"
            logger.warning(_s.format(f.name, f.file_type))
        return ""

    def build_main(self):
        self._run_tool("radiantc", [self.name + ".tcl"], quiet=True)
        self._run_tool("radiantc", [self.name + "_run.tcl"], quiet=True)

    def run_main(self):
        pass
