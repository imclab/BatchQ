####################################################################################
# Copyright (C) 2011-2012
# Troels F. Roennow, ETH Zurich
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
####################################################################################

import re

class TemplatePart(object):
    def __init__(self, string = "", parent = None):
        self._part = string
        self._next = None
        self._prev = None
        self._parent = parent

    def set_next(self, next):
        self._next = next
        if not next.prev == self: next.set_prev(self)

    def set_prev(self, prev):
        self._prev = prev
        if not prev.next == self: prev.set_next(self)

    @property
    def next(self):
        return self._next

    @property
    def prev(self):
        return self._prev

    @property
    def parent(self):
        return self._parent

    def toPython(self, indentSize = "    ", indent=""):
        return indent+"__writer__._writeToTemplate_(r\"\"\"" + self._part + "\"\"\")\n"

    def write(self, indentSize = " ",  indent =""):
        print self.toPython(indentSize ,indent)

class CodeBlock(TemplatePart):
    def __init__(self, code):
        self._code = code.strip()
        super(CodeBlock,self).__init__()

    def clear(self, string):
        i = 0
        n = len(string)
        while i < n and string[i] == " ":
            i+=1
        return i, string.strip()

    def toPython(self, indentSize = "    ", indent=""):
        lines = self._code.split("\n")
        indentsize = -1
        lastc = 0
        i = 0
        code = ""
        n = len(lines)
        for i in range(0,n):
            line = lines[i]

            c, nl = self.clear(line)
            if c != lastc and indentsize == -1:
                indentsize = lastc -c if c< lastc else  c- lastc
#            if i == n-1:
#                code += indent+"self._writeToTemplate_("+nl+")\n"
#            else:
            code += indent+indentSize * (c/indentsize) + nl+"\n"
            i+=1

        return code




class PartialCodeBlock(TemplatePart):
    def __init__(self, code, first = ""):        
        self._code = code
        self._next = None
        self._child = TemplatePart(first, parent =self)
        super(PartialCodeBlock,self).__init__()

    @property
    def child(self):
        return self._child

    def toPython(self, indentSize = "    ", indent=""):
        code = indent+self._code.strip() + "\n"
        n =  self._child
        while not n is None:
            code += n.toPython(indentSize,indentSize+indent)
            n = n.next
        return code

class GetVariable(TemplatePart):
    def __init__(self, var):
        self._var = var
        super(GetVariable,self).__init__()


    def toPython(self, indentSize = "    ", indent=""):
        return indent+"__writer__._writeToTemplate_("+self._var.strip()+")\n"



class Template(object):
    code_block_start = r"/*:"
    code_block_end = r":*/"
    partial_code_start = r"//:"
    partial_code_end = r"//!"
    variable_start = r"{{"
    variable_end = r"}}"    
    string_start = "\""
    string_end = "\""    

    conversions = {"/*:":"/\*:",  ":*/": ":\*/", "//:": "//:", "//!": "//!", "{{": "\{\{", "}}": "\}\}","\"": "\""}


    def __init__(self, string):
        self._template = string
        self._tokens = []
        self._filename = "noname"
        pattern = ""
        for key,val in self.conversions.iteritems():
            if not pattern == "": pattern += "|"
            pattern +=val
            self._tokens+=[key,]
        pattern = "("+pattern+")"

        self._pattern = re.compile(pattern);
        lst = self._pattern.split(self._template)

        inside_string = False
        templatestr = ""
        last_templatepart = TemplatePart()
        self._compiled_template = last_templatepart

        NLst =len(lst)
        i = 0
        while i<NLst:
            a = lst[i]
            if a in self._tokens:
                if not inside_string and a == self.string_start:
                    templatestr += a
                    inside_string = True
                elif inside_string and a == self.string_end:
                    templatestr += a
                    inside_string = False
                elif not inside_string:
                    n = TemplatePart(templatestr)
                    if not last_templatepart is None: last_templatepart.set_next(n)
                    last_templatepart = n

                    templatestr = ""
                    if a == self.code_block_start:
                        code = ""
                        i+=1
                        a = lst[i]
                        while a != self.code_block_end:
                            code+= a
                            i+=1
                            a = lst[i]
                        cb = CodeBlock(code)
                        if not last_templatepart is None: last_templatepart.set_next(cb)
                        last_templatepart = cb
                    elif a == self.variable_start:
                        var = ""
                        i+=1
                        a = lst[i]
                        while a != self.variable_end:
                            var+= a
                            i+=1
                            a = lst[i]
                        cb = GetVariable(var)
                        if not last_templatepart is None: last_templatepart.set_next(cb)
                        last_templatepart = cb
                    elif a == self.partial_code_start:
                        i+=1
                        a = lst[i]
                        args = a.split("\n",1)
                        cb = PartialCodeBlock(*args) 
                        if not last_templatepart is None: last_templatepart.set_next(cb)
                        last_templatepart = cb.child                      
                    elif a == self.partial_code_end:
                        prev = last_templatepart.prev
                        last = last_templatepart
                        while not prev is None:
                            last = prev
                            prev = prev.prev
                        last_templatepart = last.parent
            else:
                templatestr += a
            i+=1
        
        n = TemplatePart(templatestr)
        if not last_templatepart is None: last_templatepart.set_next(n)
        last_templatepart = n

        self._dict = {}

    def render(self, dictionary):
        pass


    def __getitem__(self, key):
        l = key.rsplit("|",1)
        if len(l) == 1:
            if not key in dict: return ""
            return self._dict[key]
        else:
            a = l[1].split(":",1)
            if len(a) == 1: return getattr(self, a[0])(self.__getitem__(l[0]))
            args = [l[0],] + a.split(",")
            return getattr(self, a[0])(self.__getitem__(args))

    def upper(self, s):
        return s.upper()

    def _toPython_(self):
        code =""
        n = self._compiled_template
        while not n is None:
            code+=n.toPython()
            n = n.next
        return code

    def set_filename(self, filename):
        self._filename = filename

    def render(self, context = {}):
        class Writer(object):
            def __init__(self):
                self._rendered = ""

            def _writeToTemplate_(self,tmp):
                self._rendered +=str(tmp)

        context['__writer__'] = Writer()
#        print self._toPython_() 
        try:
            exec compile(self._toPython_(), filename = self._filename, mode = 'exec') in  context
        except:
            print self._toPython_() 
            raise
        return context['__writer__']._rendered


    def write(self):
        n = self._compiled_template
        while not n is None:
            n.write()
            n = n.next
        

if __name__ == "__main__":
    test = Template(r"""
#include<iostream>
using namespace std;
//: for a in range(1,10):
// A lot of commments ... {{a}}
//!

int main() {
  double /*: ','.join(["res%d" % a for a in range(1,N)])  :*/;
  return 0;
}
""")
    
    print test.render({'N': 5})
    
