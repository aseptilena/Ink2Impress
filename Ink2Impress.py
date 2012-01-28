"""\
Ink2Impress.py

Create impress.js presentation graphically in Inkscape!

Still WIP, but can already create some awesome stuff!

Known Issues:
	1) Can't handle 180d rotations
	2) Can't handle transform=scale
	3) Some resolution issues
"""

from lxml import etree
import re
import math

#TODO: handle transform="scale(...)"

TRANSFORM_MATRIX_PAT = r"matrix\(([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*)\)"
TRANSFORM_TRANSLATE_PAT = r"translate\(([^,]*),([^,]*)\)"
TRANSFORM_SCALE_PAT = r"scale\(([^,]*),([^,]*)\)"

class Rect(object):
    def __init__(self, x, y, h, w, r):
        self.x = x
        self.y = y
        self.h = h
        self.w = w
        self.r = r

def parse_matrix(mat):
    """ Returns (rotation, x, y)
    Assumes no scaling in the matrix.
    """
    matrix_parts = re.match(TRANSFORM_MATRIX_PAT, mat).groups()
    
    rotation = math.atan2(-float(matrix_parts[2]), float(matrix_parts[0]))
    rotation = math.degrees(rotation)
    
    x = float(matrix_parts[-2])
    y = float(matrix_parts[-1])
    
    return rotation, x, y

def parse_translate(trans):
    #import pdb;pdb.set_trace()
    translate_parts = re.match(TRANSFORM_TRANSLATE_PAT, trans).groups()
    
    x = float(translate_parts[0])
    y = float(translate_parts[1])
    
    return 0, x, y

def parse_scale(scale):
    #import pdb;pdb.set_trace()
    scale_parts = re.match(TRANSFORM_SCALE_PAT, trans).groups()
    
    if "-1" == scale_parts[0] == scale_parts[1]:
        return 180, 0, 0
    
    return 0, 0, 0


def parse_transform(value):
    for parser in [parse_translate, parse_matrix, parse_scale]:
        try:
            return parser(value)
        except:
            pass
    return 0,0,0

def extract_rect_data(rect):
    try:
        g_r, g_x, g_y = parse_transform(rect.get("transform"))
    except:
        g_r, g_x, g_y = 0, 0, 0
    
    
    h = float(rect.get("height"))
    w = float(rect.get("width"))
    
    r = g_r
    l_x = float(rect.get("x")) + w/2
    l_y = float(rect.get("y")) + h/2
    r_r = math.radians(g_r)
    x = l_x * math.cos(r_r) - l_y * math.sin(r_r)
    y = l_x * math.sin(r_r) + l_y * math.cos(r_r)
    
    
    x += g_x
    y += g_y
    
    return Rect(x, y, h, w, r)

def create_impress(svg_tree):
    # Get the <svg> node
    
    #import pdb; pdb.set_trace()
    svg_root = svg_tree.getroot()
    
    # Get all layers (<g> nodes under the <svg> node)
    # First layer is the graphics, the second is the layout.
    layers = svg_root.xpath("g")
    graphics_layer = layers[0]
    layout_layer = layers[1]
    
    # Rectify the location of each layer
    #graphics_layer.set("transform","translate(0,0)")
    
    # Get scales and locations from the layout layer
    # Each <rect> in this layer is a step in the impress.js presentation.
    step_rects = layout_layer.xpath("rect")
    
    # Go over all the rects and extract location, rotation and size
    step_rects_data = [extract_rect_data(rect) for rect in step_rects]
    
    # Set smallest sizes as scale base
    base_height = min([data.h for data in step_rects_data])
    base_width = min([data.w for data in step_rects_data])
    base_height = BASE_HEIGHT
    base_width = BASE_WIDTH
    
    # Create a <div> from each layout <rect>
    divs = []
    for data in step_rects_data:
        scale = max(data.h / base_height, data.w / base_width)
        rotate = data.r
        x = data.x
        y = data.y
        div = etree.Element("div")
        div.set("data-scale",str(scale))
        div.set("data-rotate", str(rotate))
        div.set("data-x", str(x))
        div.set("data-y", str(y))
        div.set("class", "step")
        # Add empty data - cause we have to...
        p = etree.Element("p", style="width:10;height:10;display:block")
        p.text = " "
        div.append(p)
        divs.append(div)
        
    # Wrap the graphics layer in a <div> tag, use the width and height of the <svg> tag.
    graphics_wrapper_text = (
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="%s" height="%s"></svg>' %
         (svg_root.get("width"), svg_root.get("height"))
         )
    graphics_div = etree.fromstring(graphics_wrapper_text)
    graphics_div.append(graphics_layer)
    
    # Put all <div>s in a nice HTML page
    
    # Build the HTML template
    base_html_text = """\
<html>
    <head>
    </head>
    <body>
    
        <div id="impress">
        </div>
    
        <script type="text/javascript" src="js/impress.js">;</script>
    </body>
</html>\
"""
    base_html = etree.fromstring(base_html_text)
    
    # Get the impress <div>
    impress_div = base_html.xpath("//div")[0]
    
    # Append all layout <div> nodes into the impress one
    for div in divs:
        impress_div.append(div)
        
    # Append the graphics <div> too
    impress_div.append(graphics_div)
    
    # String-ize the result and return it
    # Don't forget the <!doctype html> !
    result_text = "<!doctype html>\n" + etree.tostring(base_html, pretty_print=True)
    return result_text

def main():
    import sys
    
    if len(sys.argv) != 3:
        print "Usage: %s <source_svg> <target_html>" % (sys.argv[0],)
        return
    
    #HACK: removing the xmlns issue...
    svg_text = open(sys.argv[1]).read()
    svg_text = svg_text.replace('xmlns="http://www.w3.org/2000/svg"', "", 1)
    svg_root = etree.fromstring(svg_text)
    svg_tree = svg_root.getroottree()
        
    #svg_tree = etree.parse(sys.argv[1])
    html_text = create_impress(svg_tree)
    open(sys.argv[2], "wb").write(html_text)

if __name__ == '__main__':
    main()
    
    