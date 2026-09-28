import frappe
import hashlib
import json

class FormCompiler:
    def __init__(self, form_id):
        self.form_id = form_id
        self.form_doc = frappe.get_doc("Form", self.form_id)
        
    def compile(self):
        schema = self._build_schema()
        mapping = self._build_mapping()
        
        schema_json = json.dumps(schema, separators=(",", ":"))
        mapping_json = json.dumps(mapping, separators=(",", ":"))
        
        # Calculate schema hash
        theme_json = self.form_doc.theme_overrides_json or "{}"
        success_schema_json = self.form_doc.success_schema_json or "{}"

        # The hash decides whether the builder offers "Update published form".
        # Theme and success-page edits change what visitors see, so they have to
        # be part of it — otherwise a design change never looks publishable.
        hash_payload = schema_json + mapping_json + theme_json + success_schema_json
        schema_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

        return {
            "schema_json": schema_json,
            "mapping_json": mapping_json,
            "schema_hash": schema_hash,
            "theme_json": theme_json,
            "success_schema_json": success_schema_json,
            "runtime_settings_json": json.dumps({
                "access_mode": self.form_doc.access_mode,
                "record_strategy": self.form_doc.record_strategy,
                "success_mode": self.form_doc.success_mode,
            })
        }
        
    # Everything the public renderer needs. The snapshot is what visitors are
    # served, so dropping a property here silently changes the live form:
    # layout indices, help text and conditional logic all have to be captured.
    SCHEMA_FIELD_PROPS = (
        "field_key",
        "fieldname",
        "label",
        "fieldtype",
        "reqd",
        "hidden",
        "read_only",
        "options",
        "default",
        "placeholder",
        "max_length",
        "description",
        "conditional_logic",
        "row_index",
        "column_index",
        "cell_index",
        "idx",
    )

    def _build_schema(self):
        fields = []
        for field in self.form_doc.get("fields"):
            snapshot = {prop: field.get(prop) for prop in self.SCHEMA_FIELD_PROPS}
            # `required` kept as an alias for older consumers of the snapshot.
            snapshot["required"] = field.reqd
            fields.append(snapshot)

        return {
            "title": self.form_doc.title,
            "route": self.form_doc.route,
            "description": self.form_doc.description,
            "success_title": self.form_doc.success_title,
            "success_description": self.form_doc.success_description,
            "allow_incomplete": self.form_doc.allow_incomplete,
            "login_required": self.form_doc.login_required,
            "fields": fields,
        }

    def _build_mapping(self):
        fields = []
        for field in self.form_doc.get("fields"):
            if field.source_type == "Target Field":
                fields.append({
                    "field_key": field.field_key,
                    "mapping_type": field.mapping_type,
                    "target_fieldname": field.target_field
                })
        return {
            "target_doctype": self.form_doc.target_doctype,
            "fields": fields
        }

    def publish(self):
        compiled = self.compile()
        
        # Determine next version
        last_version = frappe.db.get_value(
            "FP Form Version", 
            {"form": self.form_id}, 
            "version_number", 
            order_by="version_number desc"
        ) or 0
        
        next_version = last_version + 1
        
        version_doc = frappe.new_doc("FP Form Version")
        version_doc.form = self.form_id
        version_doc.version_number = next_version
        version_doc.published_at = frappe.utils.now_datetime()
        version_doc.published_by = frappe.session.user
        
        version_doc.update(compiled)
        version_doc.insert(ignore_permissions=True)
        
        self.form_doc.db_set("status", "Published")
        self.form_doc.db_set("active_version", version_doc.name)
        self.form_doc.db_set("is_published", 1)
        
        return version_doc
