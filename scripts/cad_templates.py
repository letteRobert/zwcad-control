"""Offline paper-mm frame/title template. Requires ezdxf; never connects to CAD.

Field/block design informed by local autocad-drawing; implementation is specific
to zwcad-control. Output is a generic template, not a compliance certificate.
"""
import argparse
import json
from pathlib import Path
import ezdxf

PAPER = {'A0':(1189,841),'A1':(841,594),'A2':(594,420),'A3':(420,297),'A4':(297,210)}
FIELDS = ('UNIT','TITLE','NUMBER','SCALE','MATERIAL','DESIGNER','DATE')

def generate(output, size='A3', portrait=False, values=None, title=True):
    output = Path(output)
    if output.exists():
        raise FileExistsError(f'Output already exists: {output}')
    values = {} if values is None else values
    if not isinstance(values, dict) or set(values)-set(FIELDS):
        raise ValueError('Fields must be an object using: '+', '.join(FIELDS))
    if any(not isinstance(v,str) for v in values.values()):
        raise ValueError('All field values must be strings')
    w,h = PAPER[size]
    if portrait: w,h = h,w
    margin = 10 if size in ('A0','A1') else 5
    doc = ezdxf.new('R2018', setup=True)
    doc.units = 4  # paper millimetres; never adopt this for a survey model
    doc.layers.add('ZW_FRAME',color=7)
    doc.layers.add('ZW_TITLE',color=7)
    doc.styles.add('ZW_TITLE_TEXT',font='simsun.ttf')
    msp = doc.modelspace()
    msp.add_lwpolyline([(25,margin),(w-margin,margin),(w-margin,h-margin),(25,h-margin)],close=True,dxfattribs={'layer':'ZW_FRAME'})
    if title:
        block = doc.blocks.new('ZW_TITLE_V1')
        for a,b in [((0,0),(180,0)),((180,0),(180,56)),((180,56),(0,56)),((0,56),(0,0)),
                    ((0,14),(180,14)),((0,28),(180,28)),((0,42),(180,42)),
                    ((90,14),(90,28)),((60,0),(60,14)),((120,0),(120,14))]:
            block.add_line(a,b,dxfattribs={'layer':'0'})
        cells = [('UNIT','单位',0,42),('TITLE','图名',0,28),('NUMBER','图号',0,14),
                 ('SCALE','比例',90,14),('MATERIAL','材料',0,0),
                 ('DESIGNER','设计',60,0),('DATE','日期',120,0)]
        for tag,label,x,y in cells:
            block.add_text(label,height=2.5,dxfattribs={'layer':'0','style':'ZW_TITLE_TEXT'}).set_placement((x+2,y+10))
            block.add_attdef(tag,insert=(x+2,y+4),text='',height=3.5,dxfattribs={'layer':'0','style':'ZW_TITLE_TEXT'})
        insert = msp.add_blockref('ZW_TITLE_V1',(w-margin-180,margin),dxfattribs={'layer':'ZW_TITLE'})
        insert.add_auto_attribs({tag:values.get(tag,'') for tag in FIELDS})
    if doc.audit().has_errors:
        raise ValueError('DXF audit failed before save')
    # Exclusive creation preserves existing outputs even if another process races.
    with output.open('x',encoding=doc.output_encoding,errors='dxfreplace') as stream:
        doc.write(stream)
    readback = ezdxf.readfile(output)
    if readback.audit().has_errors:
        raise ValueError(f'Readback audit failed: {output}')
    if title:
        ins = list(readback.modelspace().query('INSERT'))
        actual = {a.dxf.tag:a.dxf.text for a in ins[0].attribs}
        if actual != {tag:values.get(tag,'') for tag in FIELDS}:
            raise ValueError(f'Attribute readback failed: {output}')
    return output

def main():
    parser=argparse.ArgumentParser(description='Generate a fresh paper-mm DXF frame and editable title block; no CAD connection.')
    parser.add_argument('--size',choices=PAPER,default='A3')
    parser.add_argument('--portrait',action='store_true')
    parser.add_argument('--frame-only',action='store_true')
    parser.add_argument('--fields',help='UTF-8 JSON object: UNIT TITLE NUMBER SCALE MATERIAL DESIGNER DATE')
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    try:
        values=json.loads(Path(args.fields).read_text(encoding='utf-8-sig')) if args.fields else {}
        path=generate(args.out,args.size,args.portrait,values,not args.frame_only)
    except (ValueError,OSError) as error:
        parser.exit(1,str(error)+'\n')
    print(json.dumps({'output':str(path.resolve()),'units':'paper-mm','audit':'passed','cad_visual_check':'pending'},ensure_ascii=False))

if __name__=='__main__': main()
