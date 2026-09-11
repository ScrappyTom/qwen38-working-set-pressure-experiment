import ast


class UnarySimplifier(ast.NodeTransformer):
    def visit_UnaryOp(self, node):
        node = self.generic_visit(node)
        if isinstance(node.op, (ast.UAdd, ast.USub)):
            return ast.copy_location(node.operand, node)
        return node
