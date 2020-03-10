from collections import OrderedDict
from warnings import warn

try:
    import lxml.etree as ET

    # If we're using lxml we have to do some extra work to support namespaces,
    # so we have a variable to check whether we're using lxml:
    USING_LXML = True
    # Note that lxml is now "required" - it's listed as a requirement in
    # setup.py and is needed for the tests to pass.
    # However, stdlib etree still exists as an unsupported feature.
except ImportError:
    import xml.etree.ElementTree as ET

    USING_LXML = False
    warn("Using stdlib etree may work, but is not supported. Please install lxml.")
from flattentool.exceptions import DataErrorWarning
from flattentool.sort_xml import sort_element, XMLSchemaWalker


def sort_attributes(data):
    attribs = []
    other = []
    for k, v in data.items():
        (other, attribs)[k.startswith("@")].append((k, v))
    return OrderedDict(sorted(attribs) + other)


def child_to_xml(parent_el, tagname, child, toplevel=False, nsmap=None):
    if hasattr(child, "items"):
        child_el = dict_to_xml(child, tagname, toplevel=False, nsmap=nsmap)
        if child_el is not None:
            parent_el.append(child_el)
    else:
        if tagname.startswith("@"):
            if USING_LXML and toplevel and tagname.startswith("@xmlns"):
                nsmap[tagname[1:].split(":", 1)[1]] = str(child)
                return
            try:
                attr_name = tagname[1:]
                if USING_LXML and ":" in attr_name:
                    attr_name = (
                        "{"
                        + nsmap.get(attr_name.split(":", 1)[0], "")
                        + "}"
                        + attr_name.split(":", 1)[1]
                    )
                parent_el.attrib[attr_name] = str(child)
            except ValueError as e:
                warn(str(e), DataErrorWarning)
        elif tagname == "text()":
            parent_el.text = str(child)
        else:
            raise ("Everything should end with text() or an attribute!")


def dict_to_xml(data, tagname, toplevel=True, nsmap=None):
    if USING_LXML and ":" in tagname and not toplevel:
        tagname = (
            "{"
            + nsmap.get(tagname.split(":", 1)[0], "")
            + "}"
            + tagname.split(":", 1)[1]
        )
    try:
        if USING_LXML:
            el = ET.Element(tagname, nsmap=nsmap)
        else:
            el = ET.Element(tagname)
    except ValueError as e:
        warn(str(e), DataErrorWarning)
        return

    if USING_LXML:
        data = sort_attributes(data)

    for k, v in data.items():
        if type(v) == list:
            for item in v:
                child_to_xml(el, k, item, nsmap=nsmap)
        else:
            child_to_xml(el, k, v, toplevel=toplevel, nsmap=nsmap)
    return el


def toxml(
    data,
    xml_root_tag,
    xml_schemas=None,
    root_list_path="iati-activity",
    xml_comment=None,
):
    nsmap = {
        # This is "bound by definition" - see https://www.w3.org/XML/1998/namespace
        "xml": "http://www.w3.org/XML/1998/namespace"
    }
    root = dict_to_xml(data, xml_root_tag, nsmap=nsmap)
    if xml_schemas is not None:
        schema_dict = XMLSchemaWalker(xml_schemas).create_schema_dict(root_list_path)
        for element in root:
            sort_element(element, schema_dict)
    if xml_comment is None:
        xml_comment = "XML generated by flatten-tool"
    comment = ET.Comment(xml_comment)
    root.insert(0, comment)
    if USING_LXML:
        return ET.tostring(
            root, pretty_print=True, xml_declaration=True, encoding="utf-8"
        )
    else:
        return ET.tostring(root)
