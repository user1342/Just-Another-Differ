# JAD - Just Another Differ

import argparse
import json
import re
import tempfile
import webbrowser
from pathlib import Path
from pprint import pprint

from fuzzywuzzy import fuzz
from jinja2 import Template
from tqdm import tqdm

from GhidraBridge.ghidra_bridge import GhidraBridge


class differ():
    def _parse_args(self):
        """
        Parse and return the command-line arguments.

        Initializes an argument parser and defines required arguments for the
        paths to two binary files that need to be compared.

        :return: Namespace object with provided arguments
        """
        parser = argparse.ArgumentParser(
            description='Command-line interface for Function Change Differ')

        parser.add_argument('--binary-one', '-b1', required=True, type=str,
                            help='Path to the base binary (i.e. binary 1)')
        parser.add_argument('--binary-two', '-b2', required=True, type=str,
                            help='Path to the secondary binary (i.e. binary 2)')

        # Create a mutually exclusive group for --function and --binary
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--json-output', type=str, help='Path to a json file for a simple map output')
        group.add_argument('--html-output', type=str, help='Path to a html file for a html output')

        args = parser.parse_args()
        return args

    def _get_code_from_decom_file(self, path_to_file):
        """
        Read and extract the main code block from a decompiled file.

        Opens the file at the given path, reads its content, and uses a regular
        expression to extract the main code block. If no block is matched, returns
        the whole file content.

        :param path_to_file: Path to the file to be read.
        :return: String containing the main code block or the entire file content.
        """
        with open(path_to_file, "r") as file:
            code = file.read()
            pattern = re.compile(r'\{([^}]*)\}', re.DOTALL)
            match = pattern.search(code)

            if match and match.group(1).strip():
                return match.group(1).strip()
            else:
                return code

    def create_html_output(self, dict_of_function_similarities, out_file):
        '''
        Generate an HTML file displaying the function comparison results.

        :param dict_of_function_similarities: Dictionary containing the comparison results.
        :param output_dir: Directory where the HTML file will be saved.
        '''
        template_str = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Function Comparison Report</title>
            <style>
                body { font-family: Arial, sans-serif; }
                .codeblock-container { display: flex; }
                .codeblock {
                    background-color: #f0f0f0;
                    padding: 10px;
                    border-radius: 5px;
                    flex: 1;
                    margin: 5px;
                }
                .codeblock h3 { cursor: pointer; }
                .codeblock pre { display: none; }
                .content { display: none; }
                .visible { display: block; }
            </style>
            <script>
                function toggleCodeBlock(id) {
                    var content = document.getElementById(id);
                    var displayValue = content.style.display === "none" ? "block" : "none";
                    content.style.display = displayValue;
                }
            </script>
        </head>
        <body>
            <h1>Function Comparison Report</h1>
            <ul>
                {% for function_name, details in dict_of_function_similarities.items() %}
                <li>
                    <h2 class="function-header" onclick="toggleCodeBlock('{{ function_name }}_content')">{{ function_name }} &rarr; {{ details.binary_two_name }}</h2>
                    <div id="{{ function_name }}_content" class="content">
                        <p>Name: {{ details.comparison_binary_function_name }}</p>
                        <p>Confidence: {{ details.confidence }}%</p>
                    </div>
                </li>
                {% endfor %}
            </ul>
        </body>
        </html>
        '''

        # Create Jinja2 template from the template string
        template = Template(template_str)

        # Render the template with the provided data
        html = template.render(dict_of_function_similarities=dict_of_function_similarities)

        # Write the rendered HTML to a file
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(html)

    def entry(self):
        """
        The main entry point for the differ tool.

        Parses command-line arguments to get paths of two binary files. It then
        uses GhidraBridge to decompile these binaries, and compares the decompiled
        functions using fuzzy string matching. The results showing similarities
        between functions of the two binaries are printed.

        :return: None. The function produces a text, html, or stdout mapping
        """
        args = self._parse_args()

        dict_of_function_similarities = {}
        if args.binary_one and args.binary_two:
            binary_one_path = args.binary_one
            binary_two_path = args.binary_two

            with tempfile.TemporaryDirectory() as binary_one_decom_output:
                with tempfile.TemporaryDirectory() as binary_two_decom_output:
                    g_bridge = GhidraBridge()
                    g_bridge.decompile_binaries_functions(binary_one_path, binary_one_decom_output)
                    g_bridge.decompile_binaries_functions(binary_two_path, binary_two_decom_output)

                    paths_to_binary_one_functions = []
                    for path in Path(binary_one_decom_output).iterdir():
                        paths_to_binary_one_functions.append(path)

                    scores_for_function_one = {}
                    for binary_one_function_file_path in tqdm(paths_to_binary_one_functions,
                                                              desc="Iterating over decompiled binaries in '{}'".format(
                                                                      binary_one_path)):
                        binary_one_name, binary_one_function_name, *binary_one_epoc = Path(
                            binary_one_function_file_path).name.split("__")
                        binary_one_code = self._get_code_from_decom_file(binary_one_function_file_path)

                        for binary_two_function_file_path in Path(binary_two_decom_output).iterdir():
                            binary_two_name, binary_two_function_name, *binary_two_epoc = Path(
                                binary_two_function_file_path).name.split("__")
                            binary_two_code = self._get_code_from_decom_file(binary_two_function_file_path)

                            score = fuzz.ratio(binary_one_code, binary_two_code)

                            scores_for_function_one[binary_two_function_name] = score

                        highest_score = 0
                        highest_score_name = ""
                        for function_two_name in scores_for_function_one:
                            score = scores_for_function_one[function_two_name]
                            if score > highest_score:
                                highest_score_name = function_two_name
                                highest_score = score

                        dict_of_function_similarities[binary_one_function_name] = {
                            "comparison_binary_function_name": highest_score_name, "confidence": highest_score}

        if args.json_output and not args.html_output:
            with open(args.json_output, 'w') as file:
                json.dump(dict_of_function_similarities, file, indent=4)
            print("Json file dumped at '{}'".format(args.json_output))

        elif args.html_output and not args.json_output:
            self.create_html_output(dict_of_function_similarities, args.html_output)
            print("HTML file created at '{}'".format(args.html_output))
            webbrowser.open_new_tab(args.html_output)

        else:
            pprint(dict_of_function_similarities)


if __name__ == '__main__':
    code_differ = differ()
    code_differ.entry()
