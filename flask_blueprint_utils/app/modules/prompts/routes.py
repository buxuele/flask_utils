from flask import render_template, request, redirect, url_for, jsonify
from . import prompts_bp # Import the blueprint
from .models import Prompt # Import the Prompt model
from app.extensions import db # Import the db instance

# Note: The original app.py had url_prefix='/prompts' for these routes.
# This is now handled by the Blueprint registration in prompts/__init__.py

@prompts_bp.route('/') # Corresponds to old /prompts
def list_prompts():
    """提示词列表页面"""
    prompts_list = Prompt.query.order_by(Prompt.order, Prompt.created_at.desc()).all()
    # The template path is now relative to the blueprint's template_folder
    return render_template('prompts.html', prompts=prompts_list)

@prompts_bp.route('/', methods=['POST']) # Corresponds to old /prompts (POST)
def add_prompt():
    """添加新提示词"""
    content = request.form.get('content')
    if content:
        # 获取最大的order值
        max_order = db.session.query(db.func.max(Prompt.order)).scalar() or 0
        prompt = Prompt(content=content, order=max_order + 1)
        db.session.add(prompt)
        db.session.commit()
    # url_for uses '.<endpoint_name>' for blueprint routes
    return redirect(url_for('.list_prompts'))

@prompts_bp.route('/<int:prompt_id>', methods=['PUT']) # Corresponds to old /prompts/<int:prompt_id> (PUT)
def update_prompt(prompt_id):
    """更新提示词"""
    prompt = db.session.get(Prompt, prompt_id)
    if not prompt:
        return jsonify({'error': 'Prompt not found'}), 404

    data = request.get_json()
    if 'content' in data:
        prompt.content = data['content']
        db.session.commit()
    return jsonify({'status': 'success'})

@prompts_bp.route('/<int:prompt_id>', methods=['DELETE']) # Corresponds to old /prompts/<int:prompt_id> (DELETE)
def delete_prompt(prompt_id):
    """删除提示词"""
    prompt = db.session.get(Prompt, prompt_id)
    if not prompt:
        return jsonify({'error': 'Prompt not found'}), 404

    db.session.delete(prompt)
    db.session.commit()
    return '', 204

@prompts_bp.route('/reorder', methods=['POST']) # Corresponds to old /prompts/reorder
def reorder_prompts():
    """重新排序提示词"""
    data = request.get_json()
    prompt_id = data.get('prompt_id')
    new_index = data.get('new_index')

    if prompt_id is None or new_index is None:
        return jsonify({'error': 'Missing parameters'}), 400

    prompt_to_move = db.session.get(Prompt, prompt_id)
    if not prompt_to_move:
        return jsonify({'error': 'Prompt not found'}), 404

    # Query all prompts and sort them by current order
    all_prompts = Prompt.query.order_by(Prompt.order).all()

    if prompt_to_move not in all_prompts:
         # This case should ideally not happen if prompt_id is valid
        return jsonify({'error': 'Prompt to move not in current list'}), 500

    # Perform reordering
    current_list = [p for p in all_prompts if p.id != prompt_to_move.id]

    # Ensure new_index is within bounds
    if new_index < 0:
        new_index = 0
    if new_index > len(current_list):
        new_index = len(current_list)

    current_list.insert(new_index, prompt_to_move)

    # Update order for all prompts
    for i, p_item in enumerate(current_list):
        p_item.order = i

    db.session.commit()
    return jsonify({'status': 'success'})
