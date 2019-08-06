from flask import jsonify, request
from . import api
from app.models import *
import json
from ..util.custom_decorator import login_required
from flask_login import current_user


@api.route('/proGather/list')
@login_required
def get_pro_gather():
    """ 获取基本信息 """
    # if current_user.id == 4:
    # current_user_name = User.query.filter_by(id=current_user.id).first().name
    # _pros = Project.query.order_by('CASE WHEN user_id in {} THEN 0 END DESC'.format(current_user_name)).all()
    # _pros = Project.query.filter(Project.user_id.ilike('%' + current_user.id + '%'))
    # my_pros = Project.query.filter(Project.user_id.ilike('%' + current_user.id + '%')).first()
    _pros = Project.query.all()
    comm_project_id = User.query.filter(User.id == current_user.id).first().project_id
    if comm_project_id:
        my_pros = Project.query.filter(Project.id == comm_project_id).first()
    else:
        my_pros = Project.query.first()
    pro = {}
    pro_and_id = []
    pro_url = {}
    scene_config_lists = {}
    set_list = {}
    scene_list = {}
    for p in _pros:
        # pro_and_id[p.name] = p.id
        pro_and_id.append({'name': p.name, 'id': p.id})
        # 获取每个项目下的接口模块
        pro[p.name] = [{'name': m.name, 'moduleId': m.id} for m in p.modules]
        # 获取每个项目下的配置信息
        scene_config_lists[p.name] = [{'name': c.name, 'configId': c.id} for c in p.configs]
        # 获取每个项目下的用例集
        set_list[p.name] = [{'label': s.name, 'id': s.id} for s in p.case_sets]

        # 获取每个用例集的用例
        for s in p.case_sets:
            scene_list["{}".format(s.id)] = [{'label': scene.name, 'id': scene.id} for scene in
                                             Case.query.filter_by(case_set_id=s.id).all()]

        # 获取每个项目下的url
        if p.environment_choice == 'first':
            pro_url[p.name] = json.loads(p.host)
        elif p.environment_choice == 'second':
            pro_url[p.name] = json.loads(p.host_two)
        elif p.environment_choice == 'third':
            pro_url[p.name] = json.loads(p.host_three)
        elif p.environment_choice == 'fourth':
            pro_url[p.name] = json.loads(p.host_four)

    if my_pros:
        my_pros = {'pro_name': my_pros.name, 'model_list': pro[my_pros.name]}

    return jsonify(
        {'data': pro, 'urlData': pro_url, 'status': 1, 'user_pro': my_pros, 'config_name_list': scene_config_lists,
         'set_list': set_list, 'scene_list': scene_list, 'pro_and_id': pro_and_id})


@api.route('/project/find', methods=['POST'])
@login_required
def find_project():
    """ 查找项目 """
    data = request.json
    project_name = data.get('projectName')
    # a = db.session.execute(r'''
    # SELECT * FROM "project" WHERE name='测试平台';
    # ''')
    # print(a.first())
    page = data.get('page') if data.get('page') else 1
    per_page = data.get('sizePage') if data.get('sizePage') else 10
    user_data = [{'id': u.id, 'label': u.name} for u in User.query.all()]
    if project_name:
        """查询单个项目"""
        _data = Project.query.filter(Project.name.like('%{}%'.format(project_name))).all()
        total = len(_data)
        if not _data:
            return jsonify({'msg': '没有该项目', 'status': 0})
    else:
        """查询项目列表"""
        pagination = Project.query.order_by(Project.id.asc()).paginate(page, per_page=per_page, error_out=False)
        _data = pagination.items
        total = pagination.total

    project = [{'id': c.id,
                'host': c.host,
                'name': c.name,
                'choice': c.environment_choice,
                # 'principal': User.query.filter_by(id=c.user_id).first().name,
                'principal': c.user_id,
                'principal2': get_user_name(c.user_id),
                'createTime': str(c.created_time).split('.')[0],
                'updateTime': str(c.update_time).split('.')[0],
                'host_two': c.host_two, 'host_three': c.host_three, 'host_four': c.host_four} for c in _data]
    return jsonify({'data': project, 'total': total, 'status': 1, 'userData': user_data})


@api.route('/project/add', methods=['POST'])
@login_required
def add_project():
    """ 项目增加、编辑 """
    data = request.json
    project_name = data.get('projectName')
    if not project_name:
        return jsonify({'msg': '项目名称不能为空', 'status': 0})
    user_ids = json.dumps(data.get('users'), ensure_ascii=False)
    # user_ids = json.loads(data.get('users'))

    if not user_ids:
        return jsonify({'msg': '请选择负责人', 'status': 0})
    '''将用户名称转为用户ID'''
    '''user_ids2 = []
    for user_n in user_ids:
        user_id = User.query.filter(User.name == user_n).first().id
        user_ids2.append(user_id)'''
    # principal = data.get('principal')
    environment_choice = data.get('environmentChoice')
    host = json.dumps(data.get('host'))
    host_two = json.dumps(data.get('hostTwo'))
    host_three = json.dumps(data.get('hostThree'))
    host_four = json.dumps(data.get('hostFour'))
    ids = data.get('id')
    header = data.get('header')
    variable = data.get('variable')
    func_file = data.get('funcFile')
    if ids:
        old_project_data = Project.query.filter_by(id=ids).first()
        if Project.query.filter_by(name=project_name).first() and project_name != old_project_data.name:
            return jsonify({'msg': '项目名字重复', 'status': 0})
        else:
            old_project_data.name = project_name
            old_project_data.user_id = user_ids
            old_project_data.environment_choice = environment_choice
            old_project_data.host = host
            old_project_data.host_two = host_two
            old_project_data.host_three = host_three
            old_project_data.host_four = host_four
            old_project_data.headers = header
            old_project_data.variables = variable
            old_project_data.func_file = func_file
            db.session.commit()
            return jsonify({'msg': '修改成功', 'status': 1})
    else:
        if Project.query.filter_by(name=project_name).first():
            return jsonify({'msg': '项目名字重复', 'status': 0})
        else:
            new_project = Project(name=project_name,
                                  host=host,
                                  host_two=host_two,
                                  user_id=user_ids,
                                  func_file=func_file,
                                  environment_choice=environment_choice,
                                  host_three=host_three, host_four=host_four, headers=header, variables=variable)
            db.session.add(new_project)
            db.session.commit()
            return jsonify({'msg': '新建成功', 'status': 1})


@api.route('/project/del', methods=['POST'])
@login_required
def del_project():
    """ 删除项目 """
    data = request.json
    ids = data.get('id')
    pro_data = Project.query.filter_by(id=ids).first()
    # current_user_name = User.query.filter_by(id=current_user.id).first().name
    if str(current_user.id) not in pro_data.user_id:
        return jsonify({'msg': '不能删除别人创建的项目', 'status': 0})
    if pro_data.modules.all():
        return jsonify({'msg': '请先删除项目下的接口模块', 'status': 0})
    if pro_data.case_sets.all():
        return jsonify({'msg': '请先删除项目下的业务集', 'status': 0})
    if pro_data.configs.all():
        return jsonify({'msg': '请先删除项目下的业务配置', 'status': 0})
    db.session.delete(pro_data)
    return jsonify({'msg': '删除成功', 'status': 1})


@api.route('/project/edit', methods=['POST'])
@login_required
def edit_project():
    """ 返回待编辑项目信息 """
    data = request.json
    pro_id = data.get('id')
    _edit = Project.query.filter_by(id=pro_id).first()
    _data = {'pro_name': _edit.name,
             'user_id': _edit.user_id,
             'principal': _edit.principal,
             'func_file': _edit.func_file,
             'host': json.loads(_edit.host),
             'host_two': json.loads(_edit.host_two),
             'host_three': json.loads(_edit.host_three),
             'host_four': json.loads(_edit.host_four),
             'headers': json.loads(_edit.headers),
             'environment_choice': _edit.environment_choice,
             'variables': json.loads(_edit.variables)}
    return jsonify({'data': _data, 'status': 1})


def get_user_name(user_ids):
    names = []
    i = 0
    for id in json.loads(user_ids):
        names.append(User.query.filter_by(id=id).first().name + ",")
        i = i + 1
    return names
