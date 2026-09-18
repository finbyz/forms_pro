import frappe

class FormMappingEngine:
    def __init__(self, form_version_doc):
        self.form_version = form_version_doc
        self.schema = frappe.parse_json(self.form_version.schema_json)
        self.mapping = frappe.parse_json(self.form_version.mapping_json)

    def process_submission(self, payload):
        target_doc_data = {}
        
        for field in self.schema.get("fields", []):
            field_key = field.get("field_key")
            mapping_type = field.get("mapping_type", "Direct")
            target_fieldname = field.get("target_fieldname")
            
            value = payload.get(field_key)
            
            if mapping_type == "Direct":
                self._map_direct(target_doc_data, target_fieldname, value)
            elif mapping_type == "Constant":
                self._map_constant(target_doc_data, field)
            elif mapping_type == "Transform":
                self._map_transform(target_doc_data, target_fieldname, value, field)
            elif mapping_type == "Child Table":
                self._map_child_table(target_doc_data, target_fieldname, value, field)
                
        return target_doc_data

    def _map_direct(self, target_data, target_fieldname, value):
        if target_fieldname:
            target_data[target_fieldname] = value

    def _map_constant(self, target_data, field):
        target_fieldname = field.get("target_fieldname")
        constant_value = field.get("mapping_config_json", {}).get("constant")
        if target_fieldname:
            target_data[target_fieldname] = constant_value

    def _map_transform(self, target_data, target_fieldname, value, field):
        # Apply transform like Trim, Lowercase, etc.
        if target_fieldname and value is not None:
            transform = field.get("mapping_config_json", {}).get("transform")
            if transform == "Lowercase":
                target_data[target_fieldname] = str(value).lower()
            elif transform == "Trim":
                target_data[target_fieldname] = str(value).strip()
            else:
                target_data[target_fieldname] = value

    def _map_child_table(self, target_data, target_fieldname, rows, field):
        # Stub for mapping repeating row arrays into target Table items
        if target_fieldname and isinstance(rows, list):
            target_data[target_fieldname] = rows
