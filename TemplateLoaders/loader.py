import json
import os
import re

from TemplateParser.handler import Handler, ErrProcess, ErrParseTemplate


def load_templates(directory, placeholder_dir_and_file=None):
    handlers = []
    try:
        for files in os.listdir(directory):
            file = os.path.join(directory, files)
            with open(file, 'rb') as f:
                if not re.search('.json', f.name):
                    continue
                template_file = json.loads(f.read())
                handlers.append(Handler(template_file, placeholder_dir_and_file))
        return handlers
    except (TypeError, ErrParseTemplate) as ex:
        exit(ErrProcess(files, f'{ex}:{ex.args[1]}'))