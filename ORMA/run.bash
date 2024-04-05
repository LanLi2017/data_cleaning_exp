# python main.py --project_id 2124203262743 --output usecase1/table_view/table_view.gv table_view
# python main.py --project_id 2124203262743 --output usecase1/schema_view/schema_view.gv schema_view
# python main.py --project_id 2124203262743 --output usecase1/parallel_view/parallel_view.gv parallel_view
# python main.py --project_id 2124203262743 --output usecase1/modular_views/parallel_view modular_views
#
# python main.py --projimage.pngect_id 2494992270641 --output usecase2/table_view/table_view.gv table_view --combined True
# python main.py --project_id 2494992270641 --output usecase2/schema_view/schema_view.gv schema_view
# python main.py --project_id 2494992270641 --output usecase2/parallel_view/parallel_view.gv parallel_view
# python main.py --project_id 2494992270641 --output usecase2/modular_views/parallel_view modular_views

python __main__.py -i 1880722204439 -o usecase2/table_view/table_view.gv -t table_view -c True
python __main__.py -i 1880722204439 -o usecase2/schema_view/schema_view.gv -t schema_view
python __main__.py -i 1880722204439 -o usecase2/parallel_view/parallel_view -t parallel_view
python __main__.py -i 1880722204439 -o usecase2/modular_views/module_view -t modular_views