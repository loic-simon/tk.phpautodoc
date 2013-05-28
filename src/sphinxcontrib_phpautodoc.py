# -*- coding: utf-8 -*-
"""
    sphinxcontrib_wikitable
    ~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: Copyright 2012 by Takeshi KOMIYA
    :license: BSD, see LICENSE for details.
"""
import os
import re
import codecs
from phply import phpast as ast
from phply.phplex import lexer
from phply.phpparse import parser
from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import ViewList


def is_comment(node):
    if isinstance(node, ast.Comment) and node.text[0:3] == '/**':
        return True
    else:
        return False


def is_private(comment):
    if is_comment(comment):
        return re.search('@access\s+private', comment.text)
    else:
        return False


def to_funcname(function):
    if function.params is None:
        funcname = function.name
    else:
        params = []
        for param in function.params:
            label = param.name
            if param.default:
                value = param.default
                if isinstance(value, ast.Constant):
                    label += ' = %s' % value.name
                else:
                    label += ' = %s' % value

            params.append(label)

        funcname = "%s(%s)" % (function.name, ", ".join(params))

    return funcname


class PHPAutodocDirective(Directive):
    has_content = False
    optional_arguments = 1

    def run(self):
        self.indent = u''
        self.result = ViewList()

        srcdir = self.state.document.settings.env.srcdir
        filename = os.path.join(srcdir, self.arguments[0])
        self.parse(filename)
        self.state.document.settings.env.note_dependency(filename)

        node = nodes.paragraph()
        node.document = self.state.document
        self.state.nested_parse(self.result, 0, node)

        return node.children

    def add_entry(self, directive, name, comment):
        if not is_private(comment):
            self.add_directive_header(directive, name)
            self.add_comment(comment)

    def add_line(self, line, *lineno):
        self.result.append(self.indent + line, '<phpautodoc>', *lineno)

    def add_directive_header(self, directive, name):
        domain = getattr(self, 'domain', 'php')
        self.add_line(u'.. %s:%s:: %s' % (domain, directive, name))
        self.add_line('')

    def add_comment(self, comment):
        if not is_comment(comment):
            return

        for line in comment.text.splitlines():
            if re.match('^\s*/?\*+ ?', line):  # starts with '/*' or '*' ?
                line = re.sub('\s*\*/.*$', '', line)  # remove '*/' of tail
                line = re.sub('^\s*/?\*+ ?', '', line)  # remove '/*' or '*' of top

                if line:
                    self.add_line(u'  ' + line)
                else:
                    self.add_line('')

        self.add_line('')

    def parse(self, filename):
        try:
            with codecs.open(filename, 'r', 'utf-8') as f:
                tree = parser.parse(f.read(), lexer=lexer)

            self._parse(tree)
        except:
            raise

    def _parse(self, tree):
        last_node = None
        for node in tree:
            if isinstance(node, ast.Function):
                self.add_entry('function', to_funcname(node), last_node)
            elif isinstance(node, ast.Class):
                self.add_entry('class', node.name, last_node)

                if not is_private(last_node):
                    self._parse(node.nodes)
            elif isinstance(node, ast.Method):
                self.add_entry('method', to_funcname(node), last_node)

            last_node = node


def setup(app): 
    app.add_directive('phpautodoc', PHPAutodocDirective)
