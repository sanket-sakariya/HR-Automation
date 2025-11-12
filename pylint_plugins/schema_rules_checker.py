import os

import astroid
from pylint.checkers import BaseChecker
from pylint.lint import PyLinter


class SchemaRulesChecker(BaseChecker):
    """Checker enforcing Schema rules & conventions based on your guidelines."""

    name = "schema-rules-checker"
    priority = -1
    msgs = {
        "E9931": (
            "Schema class '%s' must end with 'Schema'",
            "schema-name-must-end-with-schema",
            "All schema class names must end with 'Schema'.",
        ),
        "E9932": (
            "Enum field '%s' must use Enum type with descriptive name",
            "enum-field-rule",
            "All status-like fields must use Enum with descriptive names and docstrings.",
        ),
        "E9933": (
            "Boolean field '%s' must start with 'is_' and have default=True",
            "boolean-field-rule",
            "Boolean fields must start with 'is_' and define default=True to indicate flags.",
        ),
        "E9934": (
            "Field '%s' must define type, optionality, and description using Field()",
            "field-validation-rule",
            "All schema fields must use Field() with type, optionality, default, and description.",
        ),
    }

    # ---------------- Utility Methods ----------------
    def _is_schema_class(self, node):
        """Check if the class is a schema class by verifying it inherits from BaseAppSchema."""
        if not isinstance(node, astroid.ClassDef):
            return False
        
        # Get base class names
        base_names = [b.as_string() for b in node.bases]
        
        # Check if it inherits from BaseAppSchema
        return "BaseAppSchema" in base_names

    def _get_base_names(self, node):
        return [b.as_string() for b in node.bases]

    def _get_field_assignments(self, node):
        return [n for n in node.body if isinstance(n, (astroid.Assign, astroid.AnnAssign))]

    # ---------------- Visitors ----------------
    def visit_classdef(self, node: astroid.ClassDef):
        """Check class definition rules for schemas."""
        if not self._should_check_schema(node):
            return

        self._check_schema_name(node)
        self._check_schema_fields(node)

    def _should_check_schema(self, node):
        """Determine if a class node should be checked as a schema."""
        if not node.root().file or not node.root().file.endswith("_schema.py"):
            return False
        if os.path.basename(node.root().file) == "baseapp_schema.py":
            return False
        return self._is_schema_class(node)

    def _check_schema_name(self, node):
        """Check if the schema class name ends with 'Schema'."""
        if not node.name.endswith("Schema"):
            self.add_message("schema-name-must-end-with-schema", node=node, args=(node.name,))

    def _check_schema_fields(self, node):
        """Check all fields in a schema class."""
        for assign in self._get_field_assignments(node):
            if isinstance(assign, astroid.Assign):
                field_name = assign.targets[0].as_string()
                field_value = assign.value.as_string() if hasattr(assign.value, "as_string") else ""
                field_annotation = ""
            elif isinstance(assign, astroid.AnnAssign):
                field_name = assign.target.as_string()
                field_annotation = assign.annotation.as_string() if assign.annotation else ""
                field_value = assign.value.as_string() if assign.value else None
            else:
                continue

            if self._check_boolean_field(assign, field_name, field_annotation, field_value):
                continue

            self._check_enum_field(assign, field_name, field_annotation)
            self._check_field_validation(assign, field_name, field_annotation, field_value)

    def _check_boolean_field(self, assign, field_name, field_annotation, field_value):
        """Check boolean field rules."""
        if field_annotation == "bool":
            if not field_name.startswith("is_"):
                self.add_message("boolean-field-rule", node=assign, args=(field_name,))
            elif field_value and "default=True" not in field_value and field_value != "True":
                self.add_message("boolean-field-rule", node=assign, args=(field_name,))
            elif isinstance(assign, astroid.AnnAssign) and not field_value:
                self.add_message("boolean-field-rule", node=assign, args=(field_name,))
            return True
        return False

    def _check_enum_field(self, assign, field_name, field_annotation):
        """Check enum field rules."""
        if "Enum" in field_annotation:
            if not field_name[0].isupper():
                self.add_message("enum-field-rule", node=assign, args=(field_name,))

    def _check_field_validation(self, assign, field_name, field_annotation, field_value):
        """Check that fields use Field() for validation."""
        if field_name not in ["model_config", "ConfigDict"]:
            if field_value and "Field(" not in field_value:
                self.add_message("field-validation-rule", node=assign, args=(field_name,))
            elif isinstance(assign, astroid.AnnAssign) and not field_value and not field_annotation.startswith("Optional["):
                if field_annotation in ["str", "int", "bool", "float", "UUID", "datetime"]:
                    self.add_message("field-validation-rule", node=assign, args=(field_name,))

def register(linter: PyLinter):
    """Register the checker with pylint"""
    linter.register_checker(SchemaRulesChecker(linter))
