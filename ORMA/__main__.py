import sys
import argparse

# from ORMA.orma import ORMAProcessor
from orma import ORMAProcessor


def run():
    argv = sys.argv
    # required argument
    reqs = ["input", "output"]
    parser = argparse.ArgumentParser(description='ORMA v0.0.1')
    parser.add_argument('-i', '--input',
                        help='openrefine project ID')
    parser.add_argument('-o', '--output',
                        help='workflow views')
    parser.add_argument('-t', '--type', default="table_view",
                        help='Workflow Views Type, Produce [table_view,schema_view,parallel_view,modular_views], Default: table_view')
    parser.add_argument('-c', '--combined', default=False,
                        help="Only input when you choose Table view. [with/without Parameters] Default: False")
    parser.add_argument('-dot', '--dot', default=None,
                        help="Dot Path, if not initialized will use the dot installation environment path")
    args = parser.parse_args(argv[1:])
    argobj = vars(args)
    # print(argobj)
    pas_req = True
    for req in reqs:
        if argobj[req] is None:
            pas_req = False
            break

    if pas_req:
        try:
            orma_proc = ORMAProcessor()
            # (self, project_id, output, type="table_view", combined=False, **kwargs):
            if argobj["type"] == "table_view":
                if argobj['combined']:
                    orma_proc.generate_views(project_id=argobj["input"], output=argobj["output"],
                                             type=argobj["type"], combined=argobj["combined"],
                                             )
                else:
                    orma_proc.generate_views(project_id=argobj["input"], output=argobj["output"],
                                             type=argobj["type"])

            elif argobj["type"] == "schema_view" or "parallel_view" or "modular_views":
                orma_proc.generate_views(project_id=argobj["input"], output=argobj["output"],
                                         type=argobj["type"]
                                         )
            else:
                raise BaseException("Workflow view type not recognized: {}".format(argobj["type"]))
            print("File {} generated.".format(argobj["output"]))
        except BaseException as exc:
            import traceback
            parser.print_help()
            traceback.print_exc()
    else:
        parser.print_help()


if __name__ == '__main__':
    run()
