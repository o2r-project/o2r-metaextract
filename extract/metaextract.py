'''
    Copyright (c) 2016 - o2r project

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

'''

import argparse
import datetime
import json
import os
import re
import sys
from xml.dom import minidom

import dicttoxml
import yaml
from guess_language import guess_language


def parse_exobj(parameter):
    # to do: get these from live extraction results (o2rexobj.txt)
    # want to know from this function:
    # packages, versions of packages
    # ERCIdentifier
    # uses list(...list(),list(),...) for packages
    result = ''
    return result

def parse_yaml(input_text):
    try:
        #yaml_data_dict = []
        yaml_data_dict = yaml.safe_load(input_text)
        return yaml_data_dict
    except yaml.YAMLError as exc:
        print('[metaextract] ! error, yaml parser -' + str(exc.problem_mark) + str(exc.problem))

def parse_r(input_text):
    c = 0
    meta_r_dict = {}
    for line in input_text.splitlines():
        c += 1
        for rule in rule_set_r:
            this_rule = rule.split('\t')
            m = re.match(this_rule[2], line)
            if m:
                if len(m.groups()) > 0:
                    # r comment
                    if this_rule[0] == 'comment':
                        segment = {'feature': this_rule[1], 'line': c, 'text': m.group(1)}
                    # r dependency
                    elif this_rule[0] == 'depends':
                        # get these from live extraction results (o2rexobj.txt)
                        dep_os = parse_exobj('os')
                        dep_packetsys = 'https://cloud.r-project.org/'
                        dep_ver = parse_exobj('version')
                        segment = {'operatingSystem': dep_os, 'packageSystem': dep_packetsys, 'version': dep_ver, 'line': c, 'category': check_rpacks(m.group(1)), 'packageId': m.group(1)}
                    # r other
                    else:
                        segment = {'feature': this_rule[1], 'line': c, 'text': m.group(1)}
                    meta_r_dict.setdefault(this_rule[0], []).append(segment)
    return meta_r_dict

def check_rpacks(package):
    label = ''
    if package in open(packlist_geosci).read():
        label += 'geo sciences,'
    if package in open(packlist_crantop100).read():
        label += 'CRAN Top100,'
    if len(label) < 1:
        label = 'none,'
    return label[:-1]

# extract
def do_ex(my_pathfile, out_format, out_mode, multiline, rule_set):
    print('[metaextract] processing ' + my_pathfile)
    c = 0
    output_data = None
    output_fileext = None
    # to do: create args for path_to_liveex_logfile and papersource
    erc_id = '' # find in o2r_run, get via parse_exobj()
    papersource = os.path.basename(my_pathfile)
    object_type = 'paperSourceFile'
    interaction_method = 'e.g. add docker cmd here' # find entry point in ../container/Dockerfile
    record_date = datetime.datetime.today().strftime('%Y-%m-%d')
    data_dict = {'file': my_pathfile, 'ercIdentifier': erc_id, 'generatedBy': 'metaextract.py', 'recordDateCreated': record_date , 'paperSource': papersource, 'objectType': object_type, 'interactionMethod': interaction_method}
    with open(os.path.relpath(my_pathfile), encoding='utf-8') as input_file:
        content = input_file.read()
        # apply multiline re for rmd, yaml, etc.
        if multiline:
            # try guess lang
            language = ''
            data_dict['paperLanguage'] = ''
            t = re.search(r'([\w\d\s\.\,\:]{300,1200})', content, flags=re.DOTALL)
            if t:
                data_dict.update(language = guess_language(t.group(1)))
            # process rules
            for rule in rule_set:
                this_rule = rule.split('\t')
                s = re.search(this_rule[1], content, flags=re.DOTALL)
                if s:
                    if this_rule[0].startswith('yaml'):
                        data_dict.update(parse_yaml(s.group(1)))
                    if this_rule[0].startswith('rblock'):
                        data_dict['r_codeblock'] = ''
                        data_dict.update(r_codeblock = parse_r(s.group(1)))
        else:
            # parse entire file as one code block
            data_dict.update(r_codeblock = parse_r(content))
    # save results
    if out_format == 'json':
        output_data = json.dumps(data_dict, sort_keys=True, indent=4, separators=(',', ': '))
        output_fileext = '.json'
    if out_format == 'xml':
        output_data = minidom.parseString(dicttoxml.dicttoxml(data_dict, attr_type = False)).toprettyxml(indent='\t')
        output_fileext = '.xml'
    if out_mode == '@s':
        # give out to screen
        print(output_data)
    elif out_mode == '@none':
        # silent mode
        pass
    else:
        # output path is given in <out_mode>
        timestamp = re.sub('\D', '', str(datetime.datetime.now().strftime('%Y%m%d%H:%M:%S.%f')[:-4]))
        # "meta_" prefix as distinctive feature for metabroker later in workflow
        output_filename = 'meta_' + timestamp + '_' + os.path.basename(my_pathfile)[:8].replace('.',
                                                                                                '_') + output_fileext
        output_filename = os.path.join(out_mode, output_filename)
        if not os.path.exists(out_mode):
            os.makedirs(out_mode)
        with open(output_filename, 'w', encoding='utf-8') as outfile:
            outfile.write(output_data)
        print('[metaextract] ' + str(os.stat(output_filename).st_size) + ' bytes written to ' + os.path.abspath(
            output_filename))

# main:
if __name__ == "__main__":
    if sys.version_info[0] < 3:
        # py2
        print('[metaextract] requires py3k or later')
        sys.exit()
    else:
        # py3k
        parser = argparse.ArgumentParser(description='description')
        parser.add_argument('-i', '--inputdir', help='input directory', required=True)
        parser.add_argument('-xml', '--modexml', help='output xml', action='store_true', default=False, required=False)
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('-o', '--outputdir', help='output directory for extraction docs')
        group.add_argument('-s', '--outputtostdout', help='output the result of the extraction to stdout', action='store_true', default=False)
        args = parser.parse_args()
        argsdict = vars(args)
        input_dir = argsdict['inputdir']
        output_xml = argsdict['modexml']
        output_dir = argsdict['outputdir']
        output_to_console = argsdict['outputtostdout']
        # output format
        if output_xml:
            output_format = 'xml'
        else:
            output_format = 'json'
        # output mode
        if output_to_console:
            output_mode = '@s'
        elif output_dir:
            output_mode = output_dir
        else:
            # not possible currently because output arg group is on mutual exclusive
            output_mode = '@none'

        # check args
        if input_dir:
            if not os.path.isdir(input_dir):
                print('[metaextract] ! error, input dir "'+ input_dir + '" does not exist')
                sys.exit()
        if output_dir:
            if not os.path.isdir(output_dir):
                print('[metaextract] directory"' + output_dir + '"  will be created during extraction...')

        # load rules:
        print('[metaextract] initializing')
        # rule set for r, compose as: category name TAB entry feature name TAB regex
        rule_set_r = []
        rule_set_r.append('Comment\tcomment\t' + r'#{1,3}\s{0,3}([\w\s\:]{1,})')
        #rule_set_r.append('Comment\tseperator\t' + r'#\s?([#*~+-_])\1*')
        rule_set_r.append('Comment\tcodefragment\t' + r'#{1,3}\s*(.*\=.*\(.*\))')
        rule_set_r.append('Comment\tcontact\t' + r'#{1,3}\s*(.*[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.].*)')
        rule_set_r.append('Comment\turl\t' + r'#{1,3}\s*http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        rule_set_r.append('Dependency\tinstalls\t' + r'install.packages\((.*)\)')
        rule_set_r.append('Dependency\t\t' + r'library\(\'?\"?([a-zA-Z\d\.]*)[\"\'\)]')
        rule_set_r.append('Dependency\t\t' + r'require\(\'?\"?([a-zA-Z\d\.]*)[\"\'\)]')
        rule_set_r.append('Input\tdataset\t' + r'data\..*\((.*)\)')
        rule_set_r.append('Output\tfile\t' + r'write\..*\((.*)\)')
        rule_set_r.append('Output\tresult\t' + r'(ggplot|plot|print)\((.*)\)')
        rule_set_r.append('Output\tsetseed\t' + r'set\.seed\((.*)\)')
        # rule set for rmd
        rule_set_rmd_multiline = []
        rule_set_rmd_multiline.append('yaml\t' + r'\-{3}(.*)[\.\-]{3}')
        rule_set_rmd_multiline.append('rblock\t' + r'\`{3}(.*)\`{3}')
        # other parameters
        packlist_crantop100 = 'list_crantop100.txt'
        packlist_geosci = 'list_geosci.txt'

        # process all files in input directory
        for file in os.listdir(input_dir):
            if file.lower().endswith('.r'):
                do_ex(os.path.join(input_dir, file), output_format, output_mode, False, rule_set_r)
            elif file.lower().endswith('.rmd'):
                do_ex(os.path.join(input_dir, file), output_format, output_mode, True, rule_set_rmd_multiline)
            else:
                pass
        print('[metaextract] done')
