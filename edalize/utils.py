class EdaCommands(object):
    class Command(object):
        def __init__(self, command, targets, depends, order_only_deps=[]):
            self.command = command
            self.targets = targets
            self.depends = depends
            self.order_only_deps = order_only_deps

    def __init__(self):
        self.commands = []
        self.header = "#Auto generated by Edalize\n\n"

    def add(self, command, targets, depends, order_only_deps=[]):
        self.commands.append(self.Command(command, targets, depends, order_only_deps))

    def set_default_target(self, target):
        self.default_target = target

    def write(self, outfile):
        with open(outfile, "w") as f:
            f.write(self.header)
            if not self.default_target:
                raise RuntimeError("Internal Edalize error. Missing default target")

            f.write(f"all: {self.default_target}\n")

            for c in self.commands:
                f.write(f"\n{' '.join(c.targets)}:")
                for d in c.depends:
                    f.write(" " + d)
                if c.order_only_deps:
                    f.write(" |")
                    for d in c.order_only_deps:
                        f.write(" " + d)

                f.write("\n")

                if c.command:
                    f.write(f"\t$(EDALIZE_LAUNCHER) {' '.join(c.command)}\n")