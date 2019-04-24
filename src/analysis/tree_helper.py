def make_tree_map(tree: str) -> list:
    """Return list of dictionaries representing ComponentMeasurements"""
    ret = []

    for line in tree.split("\n"):
        fields = line.split(",")
        ret.append({'node': fields[0],
                    'parent': fields[1],
                    'useful_lines': fields[2],
                    'threshold_violations': fields[3],
                    'full_name': fields[4]})

    return ret


# Empty tree
empty_tree = """Project,null,0,0,Project
Peripheral,Project,0,0,Peripheral
Shared,Project,0,0,Shared
Core,Project,0,0,Core
Control,Project,0,0,Control
Isolate,Project,0,0,Isolate"""

