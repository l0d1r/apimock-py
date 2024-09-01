import uuid

import falcon
import json
import re

import xmltodict

MESSAGE_REQUEST_NOT_MATCHES = f'request not matches'


class ErrParseTemplate(Exception):
    def __init__(self, reason, value):
        self.value = value
        self.reason = reason

    def __str__(self):
        return f"Error parse template: {self.reason}"


class ErrProcess(Exception):
    def __init__(self, template, reason):
        self.template = template
        self.reason = reason

    def __str__(self):
        return f"Process error: stop on {self.template}, Error:`{self.reason}`"


class Handler:
    __regexp_4_placeholder = "^[\\$][\\{]{0,1}[a-zA-Z0-9_.]+[\\}]"
    __placeholder_directories = 'placeholders/placeholders.json'
    __placeholders = dict()

    def __init__(self, templates, placeholder_dir_and_file=None):
        if placeholder_dir_and_file is not None:
            self.__placeholders = placeholder_dir_and_file

        self.__load_placeholders()

        if 'path' not in templates:
            raise ErrParseTemplate(f'field is require', 'path')

        self.path = templates['path']
        # quick added type
        # todo: rework this, in another method
        # self.__xml_type_flag = False
        self.__templates = templates['requests']
        self.__template_status_response = dict()
        self.__body_from_request = dict()
        self.__url_sigment_from_req = dict()
        self.__response_content_type = str()

        for method in templates['requests']:
            if method not in ['put', 'post', 'patch', 'get', 'delete']:
                raise ErrParseTemplate(f'unexpected method', method)

            if 'status' in self.__templates[method]['response']:
                self.__template_status_response[method] = self.__templates[method]['response']['status']

    def on_get(self, req, resp, **kwargs):
        # check method of request
        if 'get' not in self.__templates:
            resp.status = falcon.HTTP_400
            resp.text = MESSAGE_REQUEST_NOT_MATCHES
            return

        self.__url_sigment_from_req['get'] = kwargs
        self.__process_response(method_key='get', req=req, resp=resp)

    def on_delete(self, req, resp, **kwargs):
        # check method of request
        if 'delete' not in self.__templates:
            resp.status = falcon.HTTP_400
            resp.text = MESSAGE_REQUEST_NOT_MATCHES
            return

        self.__url_sigment_from_req['delete'] = kwargs
        self.__process_response(method_key='delete', req=req, resp=resp)

    def on_post(self, req, resp, **kwargs):
        # check method of request
        if 'post' not in self.__templates:
            resp.status = falcon.HTTP_400
            resp.text = MESSAGE_REQUEST_NOT_MATCHES
            return

        self.__url_sigment_from_req['post'] = kwargs
        self.__process_response(method_key='post', req=req, resp=resp)

    def on_put(self, req, resp, **kwargs):
        # check method of request
        if 'put' not in self.__templates:
            resp.status = falcon.HTTP_400
            resp.text = MESSAGE_REQUEST_NOT_MATCHES
            return

        self.__url_sigment_from_req['put'] = kwargs
        self.__process_response(method_key='put', req=req, resp=resp)

    def on_patch(self, req, resp, **kwargs):
        if 'patch' not in self.__templates:
            resp.status = falcon.HTTP_400
            resp.text = MESSAGE_REQUEST_NOT_MATCHES
            return

        self.__url_sigment_from_req['patch'] = kwargs
        self.__process_response(method_key='patch', req=req, resp=resp)

    def __load_placeholders(self):
        try:
            with open(self.__placeholder_directories, 'rb') as f:
                self.__placeholders = json.loads(f.read())
        except (TypeError, ErrParseTemplate) as ex:
            exit(ErrProcess(self.__placeholder_directories, f'{ex}:{ex.args[1]}'))

    def __process_response(self, method_key, req, resp: falcon.Response):
        # validate params by template
        if not self.__validate_request_params_by_templates(method_key=method_key, request_params=req.params):
            resp.media = {'message': 'parameters not matches'}
            resp.status = falcon.HTTP_400
            return
        # validate headers by template
        if not self.__validate_request_headers_by_templates(method_key=method_key, req_headers=req.headers):
            resp.media = {'message': 'headers not matches'}
            resp.status = falcon.HTTP_400
            return

        # get request body if: have
        if req.content_length:
            self.__body_from_request[method_key] = json.loads(req.bounded_stream.read())

        # validate body by template
        if not self.__validate_request_body_by_template(method_key=method_key):
            resp.media = {'message': 'body not matches'}
            resp.status = falcon.HTTP_400
            return

        resp_body = self.__process_preparation_response(_req=req, method_key=method_key,
                                                        _template_body=self.__templates[method_key]['response']['body'])
        if resp_body is None:
            resp.media = {'message': 'process err'}
            resp.status = falcon.HTTP_400
            return

        resp.status = self.__template_status_response[method_key]
        resp.media = resp_body

    def __validate_request_body_by_template(self, method_key):
        if len(self.__body_from_request) == 0:
            return True

        if len(self.__body_from_request) != 0 and 'body' not in self.__templates[method_key]['request']:
            return False

        if method_key not in self.__body_from_request:
            return True
        
        return self.__comparison_dicts(self.__body_from_request[method_key], self.__templates[method_key]['request']['body'])
    
    def __process_preparation_response(self, method_key, _req, _template_body):
        prepared_response = dict()

        if type(_template_body) is str and re.match('^\$xml:', _template_body):
            file = _template_body.split('$xml:')
            with open(file[1]) as f:
                data = xmltodict.parse(f.read())
            # self.__xml_type_flag = True
            return data

        self.__xml_type_flag = False
        for key in _template_body:
            if type(_template_body[key]) is list:
                temp_list = []
                for fields in range(len(_template_body[key])):
                    template_fields = _template_body[key][fields]
                    temp_list.append(self.__process_preparation_response(method_key=method_key, _req=_req, _template_body=template_fields))
                    print()
                prepared_response[key] = temp_list
                print()
                continue
            if type(_template_body[key]) is dict:
                # if key is dict look into while don't get string value
                prepared_response[key] = self.__process_preparation_response(method_key=method_key, _req=_req,
                                                                _template_body=_template_body[key])
            else:
                # check value by key from template
                if re.search('^\$req:', str(_template_body[key])):
                    prepared_response[key] = self.__replace_placeholder_with_value_from_request(method_key=method_key, req=_req,
                                                                                   placeholder=_template_body[key])
                    if prepared_response[key] is None:
                        return None
                    continue
                if re.search('^\$gen:uuid', str(_template_body[key])):
                    prepared_response[key] = str(uuid.uuid4())
                    continue
                if re.search('^\$pl:', str(_template_body[key])):
                    self.__load_placeholders()
                    value_without_pl = _template_body[key].split('$pl:')
                    options = value_without_pl[1].split('.')
                    prepared_response[key] = self.__get_value_from_dict_by_list_keys(self.__placeholders, options)
                    continue
                if _template_body[key] == "...":
                    prepared_response[key] = self.__replace_placeholder_with_value_from_request(method_key=method_key, req=_req,
                                                                                   placeholder=_template_body[key])
                    continue

                # validate do before
                prepared_response[key] = _template_body[key]
        return prepared_response

    def __replace_placeholder_with_value_from_request(self, method_key, req, placeholder):
        # get pl and replace here values from req
        value_without_pl = placeholder.split('$req:')
        options = value_without_pl[1].split('.')
        data = dict()
        match options[0]:
            case 'body':
                data = {'body': self.__body_from_request[method_key]}
            case 'parameters':
                data = {'parameters': req.params}
            case 'headers':
                data = {'headers': req.headers}
            case 'url':
                data = {'url': self.__url_sigment_from_req[method_key]}

        value = self.__get_value_from_dict_by_list_keys(data, options)

        if value is None:
            return None
        else:
            return value

    # def
    def __validate_request_params_by_templates(self, method_key, request_params):
        if len(request_params) == 0 and 'parameters' not in self.__templates[method_key]['request']:
            return True

        if len(request_params) != 0 and 'parameters' not in self.__templates[method_key]['request']:
            return False

        if len(request_params) == 0 and len(self.__templates[method_key]['request']['parameters']) != 0:
            return False

        for field in request_params:
            if field in self.__templates[method_key]['request']['parameters']:
                if type(self.__templates[method_key]['request']['parameters'][field]) is list:
                    list_dicts_query_param_field = dict()
                    list_dicts_query_param_field[field] = json.loads(request_params[field])
                    # check num fields in request and template
                    if len(list_dicts_query_param_field[field]) == len(self.__templates[method_key]['request']['parameters'][field]):
                        for num_dict in range(len(list_dicts_query_param_field)):
                            # for num dict in list parameters
                            if self.__comparison_dicts(list_dicts_query_param_field[field][num_dict],
                                                       self.__templates[method_key]['request']['parameters'][field]
                                                       [num_dict]):
                                continue
                            return False
                        continue
                    return False
                if type(request_params[field]) == type(self.__templates[method_key]['request']['parameters'][field]):
                    param_value_from_template = self.__templates[method_key]['request']['parameters'][field]
                    if type(request_params[field]) is dict:
                        if self.__comparison_dicts(request_params[field], self.__templates[method_key]['request']['parameters'][field]):
                            continue
                    else:
                        if self.__templates[method_key]['request']['parameters'][field] == "...":
                            continue
                        if re.search('^\$re:', str(param_value_from_template)):
                            value_without_re = param_value_from_template.split("$re:")
                            regexp = re.compile(value_without_re[1])
                            if not regexp.match(request_params[field]):
                                return False
                        elif request_params[field] != str(param_value_from_template):
                            return False
                else:
                    # if type do not match
                    return False
            else:
                # if field is not in template_request
                return False
        return True

    def __validate_request_headers_by_templates(self, method_key, req_headers):
        if 'headers' in self.__templates[method_key]['request']:
            for field in self.__templates[method_key]['request']['headers']:
                value = self.__templates[method_key]['request']['headers'][field]
                if field.upper() in req_headers:
                    if re.search('^\$re:', value):
                        value_without_re = value.split("$re:")
                        regexp = re.compile(value_without_re[1])
                        if not regexp.match(req_headers[field]):
                            return False
                    elif req_headers[field.upper()] != value:
                        return False
                else:
                    return False
        return True

    def __comparison_dicts(self, _dict, temp_dict):
        for key in _dict:
            if key not in temp_dict:
                return False

            if type(_dict[key]) is dict and type(temp_dict[key]) is dict:
                if not self.__comparison_dicts(_dict[key], temp_dict[key]):
                    return False
                else:
                    continue

            # validate value by regexp
            if type(_dict[key]) is str and re.search('^\$re:', str(temp_dict[key])):
                value_without_re = temp_dict[key].split("$re:")
                regexp = re.compile(value_without_re[1])
                if not regexp.match(_dict[key]):
                    return False

            # ignore placeholders
            if temp_dict[key] not in ['^\$gen:uuid', '...']:
                if _dict[key] == temp_dict[key]:
                    continue
                else:
                    return False
        return True

    @staticmethod
    def __get_value_from_dict_by_list_keys(_dict, needed_key):
        i = 0
        prev = _dict
        for key in needed_key:
            if key not in prev:
                return None
            prev = prev[key]
            if i == len(needed_key) - 1:
                return prev
            i += 1
        return None
