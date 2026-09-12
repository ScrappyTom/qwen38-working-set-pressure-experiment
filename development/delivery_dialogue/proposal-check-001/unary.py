import ast


class UnarySimplifier(ast.NodeTransformer):
    def visit_UnaryOp(self, node):
        node = self.generic_visit(node)
        if (
            isinstance(node.op, ast.UAdd)
            and isinstance(node.operand, ast.Constant)
            and type(node.operand.value) in (int, float)
        ):
            return ast.copy_location(node.operand, node)
        return node
