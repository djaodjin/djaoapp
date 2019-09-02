from rest_framework.schemas import openapi

class DocAutoSchema(openapi.AutoSchema):

    def get_operation(self, path, method):
        operation = super(DocAutoSchema, self).get_operation(path, method)
        method_name = getattr(self.view, method.lower())
        return operation
