import json
import types
from app.models import *
from httprunner.api import HttpRunner
from ..util.global_variable import *
from ..util.utils import encode_object
import importlib
from app import scheduler
from flask.json import JSONEncoder


class RunCase(object):

    def __init__(self, project_ids=None, environment_choice='first'):
        self.project_ids = project_ids
        self.pro_config_data = None
        self.pro_base_url = None
        self.new_report_id = None
        self.TEST_DATA = {'testcases': [], 'project_mapping': {'functions': {}, 'variables': {}}}
        self.environment_choice = environment_choice
        self.init_project_data()

    def init_project_data(self):

        pro_base_url = {}
        for pro_data in Project.query.all():
            if self.environment_choice == 'first':
                pro_base_url['{}'.format(pro_data.id)] = json.loads(pro_data.host)
            elif self.environment_choice == 'second':
                pro_base_url['{}'.format(pro_data.id)] = json.loads(pro_data.host_two)
            elif self.environment_choice == 'third':
                pro_base_url['{}'.format(pro_data.id)] = json.loads(pro_data.host_three)
            elif self.environment_choice == 'fourth':
                pro_base_url['{}'.format(pro_data.id)] = json.loads(pro_data.host_four)

        self.pro_base_url = pro_base_url
        self.pro_config(Project.query.filter_by(id=self.project_ids).first())

    def pro_config(self, project_data):
        """
        把project的配置数据解析出来
        :param project_data:
        :return:
        """
        self.TEST_DATA['project_mapping']['variables'] = {h['key']: h['value'] for h in
                                                          json.loads(project_data.variables) if h.get('key')}
        if project_data.func_file:
            self.extract_func([project_data.func_file.replace('.py', '')])

    def extract_func(self, func_list):
        """
        提取函数文件中的函数
        :param func_list: 函数文件地址list
        :return:
        """
        for f in func_list:
            func_list = importlib.reload(importlib.import_module('func_list.{}'.format(f)))
            module_functions_dict = {name: item for name, item in vars(func_list).items()
                                     if isinstance(item, types.FunctionType)}
            self.TEST_DATA['project_mapping']['functions'].update(module_functions_dict)

    def assemble_step(self, api_id=None, step_data=None, pro_base_url=None, status=False):
        """
        :param api_id:
        :param step_data:
        :param pro_base_url:
        :param status: 判断是接口调试(false)or业务用例执行(true)
        :return:
        """
        if status:
            # 为true，获取api基础信息；case只包含可改变部分所以还需要api基础信息组合成全新的用例
            api_data = ApiMsg.query.filter_by(id=step_data.api_msg_id).first()
        else:
            # 为false，基础信息和参数信息都在api里面，所以api_case = case_data，直接赋值覆盖
            api_data = ApiMsg.query.filter_by(id=api_id).first()
            step_data = api_data
            # api_data = case_data

        _data = {'name': step_data.name,
                 'request': {'method': api_data.method,
                             'files': {},
                             'data': {}}}

        # _data['request']['headers'] = {h['key']: h['value'] for h in json.loads(api_data.header)
        #                                if h['key']} if json.loads(api_data.header) else {}

        if api_data.status_url != '-1':
            _data['request']['url'] = pro_base_url['{}'.format(api_data.project_id)][
                                          int(api_data.status_url)] + api_data.url.split('?')[0]
        else:
            _data['request']['url'] = api_data.url

        if step_data.up_func:
            _data['setup_hooks'] = [step_data.up_func]

        if step_data.down_func:
            _data['teardown_hooks'] = [step_data.down_func]

        if status:
            _data['times'] = step_data.time
            if json.loads(step_data.status_param)[0]:
                if json.loads(step_data.status_param)[1]:
                    _param = json.loads(step_data.param)
                else:
                    _param = json.loads(api_data.param)
            else:
                _param = None

            if json.loads(step_data.status_variables)[0]:
                if json.loads(step_data.status_variables)[1]:
                    _json_variables = step_data.json_variable
                    _variables = json.loads(step_data.variable)
                else:
                    _json_variables = api_data.json_variable
                    _variables = json.loads(api_data.variable)
            else:
                _json_variables = None
                _variables = None

            if json.loads(step_data.status_extract)[0]:
                if json.loads(step_data.status_extract)[1]:
                    _extract = step_data.extract
                else:
                    _extract = api_data.extract
            else:
                _extract = None

            if json.loads(step_data.status_validate)[0]:
                if json.loads(step_data.status_validate)[1]:
                    _validate = step_data.validate
                else:
                    _validate = api_data.validate
            else:
                _validate = None

            if json.loads(step_data.status_header)[0]:
                if json.loads(step_data.status_header)[1]:
                    _header = json.loads(step_data.header)
                else:
                    _header = json.loads(api_data.header)
            else:
                _header = None

        else:
            _param = json.loads(api_data.param)
            _json_variables = api_data.json_variable
            _variables = json.loads(api_data.variable)
            _header = json.loads(api_data.header)
            _extract = api_data.extract
            _validate = api_data.validate

        _data['request']['params'] = {param['key']: param['value'].replace('%', '&') for param in
                                      _param if param.get('key')} if _param else {}

        _data['request']['headers'] = {headers['key']: headers['value'].replace('%', '&') for headers in
                                       _header if headers.get('key')} if _header else {}

        _data['extract'] = [{ext['key']: ext['value']} for ext in json.loads(_extract) if
                            ext.get('key')] if _extract else []

        _data['validate'] = [{val['comparator']: [val['key'], val['value']]} for val in json.loads(_validate) if
                             val.get('key')] if _validate else []

        if api_data.method == 'GET':
            pass
        elif api_data.variable_type == 'text' and _variables:
            for variable in _variables:
                if variable['param_type'] == 'string' and variable.get('key'):
                    _data['request']['files'].update({variable['key']: (None, variable['value'])})
                elif variable['param_type'] == 'file' and variable.get('key'):
                    _data['request']['files'].update({variable['key']: (
                        variable['value'].split('/')[-1], open(variable['value'], 'rb'),
                        CONTENT_TYPE['.{}'.format(variable['value'].split('.')[-1])])})

        elif api_data.variable_type == 'data' and _variables:
            for variable in _variables:
                if variable['param_type'] == 'string' and variable.get('key'):
                    _data['request']['data'].update({variable['key']: variable['value']})
                elif variable['param_type'] == 'file' and variable.get('key'):
                    _data['request']['files'].update({variable['key']: (
                        variable['value'].split('/')[-1], open(variable['value'], 'rb'),
                        CONTENT_TYPE['.{}'.format(variable['value'].split('.')[-1])])})

        elif api_data.variable_type == 'json':
            if _json_variables:
                _data['request']['json'] = json.loads(_json_variables)

        return _data

    def get_api_test(self, api_ids, project_id):
        # self.environment_choice = envValue
        """
        接口调试时，用到的方法.
        :param api_ids: 接口id列表
        :param config_id: 配置id
        :return:
        """
        scheduler.app.logger.info('本次测试的接口id：{}'.format(api_ids))
        _steps = {'teststeps': [], 'config': {'variables': {}}, 'output': ['phone']}

        if project_id:
            """
            取对应环境的配置
            """
            # config_data = Config.query.filter_by(id=config_id).first()
            config_data = Config.query.filter_by(project_id=project_id).first()

            _config = self.get_project_config(project_id)
            _steps['config']['variables'].update({v['key']: v['value'] for v in _config if v['key']})
            self.extract_func(['{}'.format(f.replace('.py', '')) for f in json.loads(config_data.func_address)])

        _steps['teststeps'] = [self.assemble_step(api_id, None, self.pro_base_url, False) for api_id in api_ids]
        self.TEST_DATA['testcases'].append(_steps)

    def get_project_config(self, project_id):
        """根据配置取不同环境数据"""
        config_data = Config.query.filter_by(project_id=project_id).first()
        if self.environment_choice == 'first':
            _config = json.loads(config_data.variables) if project_id else []
        elif self.environment_choice == 'second':
            _config = json.loads(config_data.variables_two) if project_id else []
        elif self.environment_choice == 'third':
            _config = json.loads(config_data.variables_three) if project_id else []
        elif self.environment_choice == 'fourth':
            _config = json.loads(config_data.variables_four) if project_id else []
        return _config

    def get_case_test(self, case_ids):
        """
        用例调试时，用到的方法
        :param case_ids: 用例id列表
        :return:
        """
        scheduler.app.logger.info('本次测试的用例id：{}'.format(case_ids))
        for case_id in case_ids:
            case_data = Case.query.filter_by(id=case_id).first()
            case_times = case_data.times if case_data.times else 1
            for s in range(case_times):
                _steps = {'teststeps': [], 'config': {'variables': {}, 'name': ''}}
                _steps['config']['name'] = case_data.name
                """从配置表取内置函数"""
                config_data = Config.query.filter_by(project_id=case_data.project_id).first()
                # 获取项目的配置数据
                _config = self.get_project_config(case_data.project_id)
                _steps['config']['variables'].update({v['key']: v['value'] for v in _config if v['key']})
                """从用例表中取数据"""
                # self.extract_func(['{}'.format(f.replace('.py', '')) for f in json.loads(case_data.func_address)])
                """从配置表取数据"""
                self.extract_func(['{}'.format(f.replace('.py', '')) for f in json.loads(config_data.func_address)])

                for _step in CaseData.query.filter_by(case_id=case_id).order_by(CaseData.num.asc()).all():
                    if _step.status == 'true':  # 判断步骤状态，是否执行
                        _steps['teststeps'].append(self.assemble_step(None, _step, self.pro_base_url, True))
                self.TEST_DATA['testcases'].append(_steps)

    def build_report(self, jump_res, case_ids, performer='无', taskName='无'):

        new_report = Report(
            case_names=','.join([Case.query.filter_by(id=scene_id).first().name for scene_id in case_ids]),
            project_id=self.project_ids, read_status='待阅', performer=performer,
            environment_choice=self.environment_choice,
            task_name=taskName)
        db.session.add(new_report)
        db.session.commit()

        self.new_report_id = new_report.id
        with open('{}{}.txt'.format(REPORT_ADDRESS, self.new_report_id), 'w') as f:
            f.write(jump_res)
        return new_report.id

    def run_case(self):
        scheduler.app.logger.info('测试数据：{}'.format(self.TEST_DATA))
        # res = main_ate(self.TEST_DATA)
        """失败终止测试"""
        runner = HttpRunner(failfast=False)
        runner.run(self.TEST_DATA)
        jump_res = json.dumps(runner._summary, ensure_ascii=False, default=encode_object, cls=JSONEncoder)
        return jump_res
