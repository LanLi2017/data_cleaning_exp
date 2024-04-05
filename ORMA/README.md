# idcc2021

Workflow of using ORMA

1. Download/Clone ORMA 

     `git clone https://github.com/idaks/ORMA-IDCC-2021`

2. Download OpenRefine Python Client library Dependency

     `cd ORMA-IDCC-2021`
     
     `cd refine_pkg`
     
     `git clone https://github.com/LanLi2017/OpenRefineClientPy3`


3. Check your graphviz version:
   
   Example:
   
     `dot -V`
  
     `dot - graphviz version 2.42.3 (20191010.1750)`
     
      
   If you don't have dot installed. Install the latest version Download **[Graphviz](https://www.graphviz.org/download/)**.


    1). For Mac users (ex.use Homebrew):
    
    `$ brew install graphviz`
    
    
    2). For Windows users, choose one of the methods from the **[download](https://www.graphviz.org/download/)**. website
    
    
    3). For Linux users, choose one of the methods from the **[download](https://www.graphviz.org/download/)**. website
    
    
4. Python Version 3.0+; Download **[Python](https://www.python.org/downloads/)**.
   
   `python`
   
   
   `Python 3.7.8 (default, Jul 29 2020, 16:29:47)
    [Clang 11.0.3 (clang-1103.0.32.62)] on darwin
    Type "help", "copyright", "credits" or "license" for more information.`

Change run.bash to run __main__.py (Please refer to README.md in usecase1 folder)

`> python __main__.py `

    usage: __main__.py [-h] [-i INPUT] [-o OUTPUT] [-t TYPE] [-c COMBINED]
                       [-dot DOT]
    
    ORMA v0.0.1
    
    optional arguments:
      -h, --help            show this help message and exit
      -i INPUT, --input INPUT
                            openrefine project ID
      -o OUTPUT, --output OUTPUT
                            workflow views
      -t TYPE, --type TYPE  Workflow Views Type, Produce
                            [table_view,schema_view,parallel_view,modular_views],
                            Default: table_view
      -c COMBINED, --combined COMBINED
                        Only input when you choose Table view. [with/without
                        Parameters] Default: False
      -dot DOT, --dot DOT   Dot Path, if not initialized will use the dot
                            installation environment path