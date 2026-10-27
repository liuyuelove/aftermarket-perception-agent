import xml.etree.ElementTree as ET
# import xmltodict
from lxml import etree
from lxml.builder import ElementMaker
from collections import OrderedDict
from pathlib import Path


def xml_file_gen(obj_dict_i, xml_file_path_i='voc/test.xml', img_shape_i=(3, 720, 1280)):
    '''
    Generate xml file according to object dictionary.
    
    :param obj_dict_i: object dictionary, {obj_name: {'bbox': [[x_min, y_min, x_max, y_max],]}}
    :param xml_file_path_i: xml file path
    :param img_shape_i: image shape (C, H, W)
    '''
    xml_dict = xml_dict_gen(obj_dict_i, xml_file_path_i, img_shape_i)
    write_xml_dict_to_file(xml_dict, xml_file_path_i)

def xml_dict_gen(obj_dict_i, xml_file_path_i='test.xml', img_shape_i=(3, 720, 1280)):
    '''
    Generate xml dictionary according to object dictionary.
    
    :param obj_dict_i: object dictionary, {obj_name: {'bbox': [[x_min, y_min, x_max, y_max],]}}
    :param xml_file_path_i: xml file path
    :param img_shape_i: image shape (C, H, W)
    :return: xml_dict: xml dictionary, {'annotation': {{'folder': str}, {'source': OrderedDict}, ... {'object': [OrderedDict,]}}}
    '''
    xml_dict = OrderedDict()

    xml_dict['annotation'] = OrderedDict()
    root = xml_dict['annotation']
    if isinstance(xml_file_path_i, Path):
        xml_path = xml_file_path_i
    else:
        xml_path = Path(xml_file_path_i)
    root['folder'] = str(xml_path.parent)
    root['filename'] = str(xml_path.name).replace('.xml', '.jpg')

    root['source'] = OrderedDict()
    source = root['source']
    source['database'] = 'Unknown'

    root['size'] = OrderedDict()
    size = root['size']
    size['width'] = img_shape_i[2]
    size['height'] = img_shape_i[1]
    size['depth'] = img_shape_i[0]

    root['segmented'] = '0'
    root['object'] = []
    for obj_name, obj_value in obj_dict_i.items():
        for bbox in obj_value['bbox']:
            obj_dict = OrderedDict()
            obj_dict['name'] = obj_name
            obj_dict['pose'] = 'Unspecified'
            obj_dict['truncated'] = '0'
            obj_dict['difficult'] = '0'
            obj_dict['bndbox'] = OrderedDict()
            obj_dict['bndbox']['xmin'] = bbox[0]
            obj_dict['bndbox']['ymin'] = bbox[1]
            obj_dict['bndbox']['xmax'] = bbox[2]
            obj_dict['bndbox']['ymax'] = bbox[3]
            root['object'].append(obj_dict)

    return xml_dict

def et_element_to_element_maker(et_element):
    '''
    Convert ElementTree element to ElementMaker element.
    
    :param et_element: ElementTree element
    :return: ElementMaker element
    '''
    # 创建 ElementMaker 实例
    E = ElementMaker()

    # 定义递归函数来处理子元素
    def convert_element(et_element):
        tag = et_element.tag
        attrib = et_element.attrib
        text = et_element.text.strip() if et_element.text and et_element.text.strip() else None

        # 创建当前元素
        current_element = getattr(E, tag)(*[
            convert_element(subelement) for subelement in et_element
        ], **attrib)

        # 如果有文本内容，则设置文本
        if text:
            current_element.text = text

        return current_element

    # 调用递归函数转换整个树
    new_element = convert_element(et_element)
    return new_element

def write_xml_dict_to_file(xml_dict_i, xml_file_path_i):
    '''
    Write xml dictionary to file.
    
    :param xml_dict_i: xml dictionary
    :param xml_file_path_i: xml file path
    '''
    def gen_et_element_tree(root_i, dict_i):
        for k, v in dict_i.items():
            if isinstance(v, (dict, OrderedDict)):
                child = ET.SubElement(root_i, k)
                gen_et_element_tree(child, v)
            elif isinstance(v, list):
                for obj in v:
                    child = ET.SubElement(root_i, k)
                    gen_et_element_tree(child, obj)
            else:
                child = ET.SubElement(root_i, k)
                child.text = str(v)

    root = ET.Element(list(xml_dict_i.keys())[0])
    for value in xml_dict_i.values():
        gen_et_element_tree(root, value)

    if isinstance(xml_file_path_i, Path):
        xml_path = xml_file_path_i
    else:
        xml_path = Path(xml_file_path_i)

    # 以ElementTree保存
    # tree = ET.ElementTree(root)
    # tree.write(xml_path, encoding="utf-8")
    
    # 以ElementMaker保存
    new_annotation = et_element_to_element_maker(root)
    xml_str = etree.tostring(new_annotation, pretty_print=True, encoding='unicode')
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_str)


def parse_xml_to_dict(element):
    """
    递归地将 XML 元素转换为字典。
    """
    # 如果当前元素没有子元素，则直接返回其文本内容
    if len(element) == 0:
        return element.text

    # 否则递归处理子元素
    result = {}
    for child in element:
        child_result = parse_xml_to_dict(child)
        # 如果子元素的标签已经存在于结果字典中，则将其转为列表存储
        if child.tag in result:
            if isinstance(result[child.tag], list):
                result[child.tag].append(child_result)
            else:
                result[child.tag] = [result[child.tag], child_result]
        else:
            result[child.tag] = child_result
    return result

def read_xml_to_dict(file_path):
    """
    读取 XML 文件并将其内容转换为字典。
    """
    tree = ET.parse(file_path)
    root = tree.getroot()
    return {root.tag: parse_xml_to_dict(root)}


def read_xml_to_obj_dict(xml_file_path_i):
    '''
    Read xml file and convert it to object dictionary.
    
    :param xml_file_path_i: xml file path
    :return: obj_dict: {obj_name: {'bbox': [[x_min, y_min, x_max, y_max],]}}
    '''
    
    # with open(xml_file_path_i, 'r', encoding='utf-8') as f:
    #     xml_str = f.read()
    # xml_dict = xmltodict.parse(xml_str)
    
    xml_dict = read_xml_to_dict(xml_file_path_i)
    obj_dict = {}
    if 'object' in xml_dict['annotation']:
        obj_list = xml_dict['annotation']['object']
        if isinstance(obj_list, list) == False:
            obj_list = [obj_list]
        for obj in obj_list:
            obj_name = obj['name']
            bbox = [float(obj['bndbox']['xmin']), float(obj['bndbox']['ymin']), float(obj['bndbox']['xmax']), float(obj['bndbox']['ymax'])]
            if obj_name not in obj_dict:
                obj_dict[obj_name] = {'bbox': []}
            obj_dict[obj_name]['bbox'].append(bbox)
    return obj_dict, xml_dict

def xml_crop_resize(xml_i, crop_param_i=None, resize_shape_i=None, save_path_i=None):
    '''
    xml_crop_resize
    
    :param xml_i: 源xml文件路径或xml字典
    :param crop_param_i: 裁剪参数 (crop_x0, crop_y0, crop_width, crop_height), 若为None, 则不裁剪
    :param resize_shape_i: 缩放后的图片形状 (w, h), 若为None, 则不缩放
    :param save_path_i: 输出xml保存路径, 若为None, 则不保存
    '''
    if isinstance(xml_i, str):
        xml_dict = read_xml_to_dict(xml_i)
    else:
        xml_dict = xml_i
    
    if crop_param_i is not None:
        crop_x0, crop_y0, crop_width, crop_height = crop_param_i
    else:
        crop_x0, crop_y0, crop_width, crop_height = 0, 0, int(xml_dict['annotation']['size']['width']), int(xml_dict['annotation']['size']['height'])

    if resize_shape_i is not None:
        resize_shape = resize_shape_i
    else:
        resize_shape = (crop_width, crop_height)
    resize_coeff_x, resize_coeff_y = resize_shape[0] / crop_width, resize_shape[1] / crop_height
    
    if 'object' in xml_dict['annotation']:
        obj_list = xml_dict['annotation']['object']
        if isinstance(obj_list, list) == False:
            obj_list = [obj_list]
        
        obj_list_new = []
        for obj in obj_list.copy():
            x_min, y_min, x_max, y_max = [float(obj['bndbox']['xmin']), float(obj['bndbox']['ymin']), float(obj['bndbox']['xmax']), float(obj['bndbox']['ymax'])]
            x_min = max(0, (x_min - crop_x0) * resize_coeff_x)
            y_min = max(0, (y_min - crop_y0) * resize_coeff_y)
            x_max = min(resize_shape[0]-1, (x_max - crop_x0) * resize_coeff_x)
            y_max = min(resize_shape[1]-1, (y_max - crop_y0) * resize_coeff_y)
            if x_min >= x_max or y_min >= y_max:
                obj_list.remove(obj)
            else:
                obj['bndbox']['xmin'] = str(x_min)
                obj['bndbox']['ymin'] = str(y_min)
                obj['bndbox']['xmax'] = str(x_max)
                obj['bndbox']['ymax'] = str(y_max)
                obj_list_new.append(obj)
        xml_dict['annotation']['object'] = obj_list_new
    
    xml_dict['annotation']['size']['width'] = str(resize_shape[0])
    xml_dict['annotation']['size']['height'] = str(resize_shape[1])

    if save_path_i is not None:
        write_xml_dict_to_file(xml_dict, save_path_i)
    return xml_dict
