"""Publish the custom current-limit IC symbol already embedded in the schematic."""
from pathlib import Path
from copy import deepcopy
from cad_sexpr import parse, dump, children, child, Q

directory=Path(__file__).resolve().parent/'revF-gps-expansion'
sheet=parse((directory/'gps-expansion.kicad_sch').read_text())
symbol=deepcopy(next(s for s in children(child(sheet,'lib_symbols'),'symbol') if s[1]=='Owasso:TPS2553DBVR'))
symbol[1]=Q('TPS2553DBVR')
lib=['kicad_symbol_lib',['version','20241209'],['generator',Q('kicad_symbol_editor')],symbol]
(directory/'Owasso.kicad_sym').write_text(dump(lib)+'\n')
table=parse((directory/'sym-lib-table').read_text())
if not any(child(s,'name')[1]=='Owasso' for s in children(table,'lib')):
    table.append(parse('(lib (name "Owasso") (type "KiCad") (uri "${KIPRJMOD}/Owasso.kicad_sym") (options "") (descr "Reviewed TPS2553 pin contract"))'))
(directory/'sym-lib-table').write_text(dump(table)+'\n')
