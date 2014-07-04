#!/usr/bin/env python
# Describe classes, methods and functions in a module.
# Works with user-defined modules, all Python library
# modules, including built-in modules.
from __future__ import absolute_import, print_function
import os, sys, inspect, re, logging

module_imports = []
literal_imports = []
futured = []
modules = {}
output_code = []
headers = []
   
def add(values, value):
    if value in values:
        return False
    else:
        values.append(value)
        return True

def source_module(module_name, import_line, object_name=None, alt_names=None):
    if module_name in modules:
        Log.info("Module {} already sourced. Skipping it.".format(module_name))
    else:
        module = __import__(module_name, globals(), locals(), [module_name.split('.')[-1]])
        if object_name:
            Log.info("Checking if {}.{} is a module or an object".format(module_name, object_name))
            module_object = getattr(module,object_name,None)
            Log.info("module_object type: {}".format(type(module_object)))
            if not module_object or inspect.ismodule(module_object):
                Log.info("{}.{} is a module. Sourcing it".format(module_name, object_name))
                module_name = '{}.{}'.format(module_name, object_name)
                add(alt_names, object_name)
                if module_object:
                    module = module_object
                else:
                    module = __import__(module_name, globals(), locals(), [module_name.split('.')[-1]])
            else:
                Log.info("{}.{} is an object. Sourcing parent: {}".format(module_name, object_name, module_name))
        if getattr(module,'__FLATTEN__',True):
            modules[module_name] = []
            Log.info("Sourcing module {}".format(module_name))
            process_source(module_name, inspect.getsource(module).split('\n'), is_module=True)
            Log.info("Module {} sourced successfully".format(module_name))
        else:
            Log.info("Module {} cannot be flattened. Skipping it.".format(module_name))
            add(literal_imports,import_line)


def process_source(source_name, source, is_module=False):
    SKIP = False
    aliases = []
    alt_names = []
    Log.info("Processing source of {}".format(source_name))
    process_headers = True
    for line in source:
        Log.abusive("LINE: {}".format(line.rstrip()))
        if (line.startswith('#') or not len(line.strip())) and process_headers:
            if not is_module:
                headers.append(line)
        else:
            process_headers = False
            if line.startswith('import '):
                Log.debug("Found import line: {}".format(line.rstrip()))
                for module_name in line.split('import ',1)[1].split(','):
                    module_name = module_name.strip()
                    full_module_import = 'import {}'.format(module_name)
                    if module_name.startswith(prefix):
                        Log.debug("Found module to import: {}".format(module_name))
                        if re.search(' as ', module_name):
                            alt_name = module_name.split(' as ')[1].strip()
                            Log.debug("Found alternative name: {}".format(alt_name))
                            module_name = module_name.split(' as ')[0].strip()
                            add(alt_names, alt_name)
                        else:
                            add(alt_names, module_name)
                        source_module(module_name, full_module_import)
                    else:
                        add(module_imports, module_name)
            elif re.match('from .+ import .+',line):
                Log.debug("Found from line: {}".format(line.rstrip()))
                module_name = line.split('from ',1)[1].split(' import',1)[0]
                if module_name.startswith(prefix):
                    Log.abusive("FROM: {}".format(module_name))
                    for object_name in line.split(' import ',1)[1].split(','):
                        Log.abusive("OBJECT: {}".format(object_name))
                        object_name = object_name.strip()
                        if re.search(' as ', object_name):
                            alias = object_name.split(' as ')[1].strip()
                            object_name = object_name.split(' as ')[0].strip()
                            Log.debug("Found alias: {} refers to {}".format(alias, object_name))
                            aliases.append((alias, object_name))
                        source_module(module_name, line, object_name, alt_names)
                elif module_name == '__future__':
                    for future in line.split(' import ',1)[1].split(','):
                        add(futured, future.strip())
                else:
                    add(literal_imports,line)
            elif not is_module:
                output_code.append(standarize(line, alt_names, aliases))
            else:
                # Process module source: consider indentation blocks and get only the relevant parts
                if re.match('''if *__name__ *== *["']__main__["']:''',line):
                    Log.debug("Found __main__ block in module {}. Skipping it.".format(source_name))
                    # We don't want to import the main function
                    SKIP = True
                elif line.startswith(' ') or not len(line.strip()):
                    if not SKIP:
                        line = standarize(line, alt_names, aliases)
                        Log.abusive("Appending line {}".format(line))
                        modules[source_name].append(line)
                    else:
                        Log.abusive("Skipping...")
                else:
                    SKIP = False
                    line = standarize(line, alt_names, aliases)
                    Log.abusive("Appending line {}".format(line))
                    modules[source_name].append(line)

def standarize(line, alt_names, aliases):
    Log.abusive("Standarizing line {}".format(line))
    Log.abusive("Aliases: {}, Alt_names: {}".format(aliases, alt_names))
    line = strip_alt_names(alt_names, replace_aliases(aliases, line))
    Log.abusive("Returning line {}".format(line))
    return line

def strip_alt_names(alt_names, line):
    for alt_name in alt_names:
        line = re.sub('(?<![^ (]){}\.'.format(alt_name),'',line)
    return line

def replace_aliases(aliases, line):
    for alias in aliases:
        line = re.sub('(?<![^ (]){}'.format(alias[0]), alias[1], line)
    return line


def process_headers(source):
    for line in source:
        if line.startswith('#'):
            Log.debug("Found header: {}".format(line.rstrip()))
            headers.append(line)
        elif not len(line.strip()):
            Log.abusive("Found empty line")
            headers.append(line)
        else:
            return

def build(output):
    print("".join(headers),file=output)
    print("# IMPORTS:",file=output)
    if len(futured):
        print("from __future__ import {}".format(', '.join(futured)),file=output)
    if len(module_imports):
        print("import {}".format(', '.join(module_imports)),file=output)

    for literal_import in literal_imports:
        print(literal_import,file=output)

    for name, code in modules.iteritems():
        print("\n# IMPORTED MODULE: {}".format(name),file=output)
        print('\n'.join(code),file=output)

    print('# MAIN CODE:',file=output)
    print(''.join(output_code),file=output)

class Log():
    LEVEL = 0

    @staticmethod
    def setLevel(level):
        Log.LEVEL = level

    @staticmethod
    def log(level, message):
        if level <= Log.LEVEL:
            print(message)

    @staticmethod
    def info(message):
        Log.log(1, message)

    @staticmethod
    def debug(message):
        Log.log(1, message)

    @staticmethod
    def abusive(message):
        Log.log(2, message)

if __name__ == "__main__":
    import argparse

    def get_prefix(args):
        prefix = args.prefix
        if not prefix:
            prefix = os.path.dirname(args.source).split('/')[0]
        if len(prefix):
            return "{}.".format(prefix)
        else:
            sys.exit("ERROR: Please specify a prefix")

    def get_output(args):
        outfile = args.output
        directory = args.dir
        if not os.path.exists(directory):
            os.makedirs(directory)
        if not outfile:
            outfile = os.path.basename(args.source)
        return "{}/{}".format(directory, outfile)

    parser = argparse.ArgumentParser()

    parser.add_argument("source", help="Source file to parse")
    parser.add_argument("-v", "--verbose", action="count", help="Be verbse. Use -vv or -vvv to invrease verbosity")
    parser.add_argument("-p", "--prefix", help="Prefix to be used. Defaults to the physical path of the source file")
    parser.add_argument("-o", "--output", help='Output file name. Use "-" without quotes to write to console. Defaults to the name of the source file.')
    parser.add_argument("-d", "--dir", help='Output directory. Defaults to flattened', default='flattened')

    args = parser.parse_args()
    
    Log.LEVEL = args.verbose
    prefix = get_prefix(args)
    source_file = args.source

    print("Processing sourcefile {} with prefix {}".format(source_file, prefix))
    with open(source_file, 'r') as source:
        process_source(source_file, source)

    print("{} processed successfully".format(source_file))

    if args.output == '-':
        build(sys.stdout)
    else:
        output = get_output(args)
        print("Printing results into file {}".format(output))
        with open(output,'w') as out:
            build(out)
