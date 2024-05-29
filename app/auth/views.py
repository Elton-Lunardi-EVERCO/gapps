from datetime import datetime
import logging
from secrets import token_urlsafe
from flask import (
    request,
    render_template,
    flash,
    redirect,
    Blueprint,
    url_for,
    current_app,
    abort
)
from flask_babel import lazy_gettext as _l
from flask_login import current_user, logout_user, login_user, login_required
from . import auth

from app import db
from app.models import *
from app.email import send_email
from app.utils import misc
import datetime

logger = logging.getLogger(__name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    next_page = request.args.get('next')
    if current_user.is_authenticated:
        return redirect(next_page or url_for('main.home'))
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if not (user := User.find_by_email(email)):
            flash(_l('E-mail ou senha inválida'), 'warning')
            Logs.add(f"e-mail inválido para {email}", level="warning")
            return redirect(url_for('auth.login'))
        if not user.check_password(password):
            flash(_l('E-mail ou senha inválida'), 'warning')
            Logs.add(f"senha inválida para e-mail:{email}", level="warning")
            return redirect(next_page or url_for('auth.login'))
        if not user.is_active:
            flash(_l('O usuário está inativo'), 'warning')
            Logs.add(f"usuário inativo tentou fazer login:{email}", level="warning")
            return redirect(next_page or url_for('auth.login'))
        flash("Bem-Vindo")
        Logs.add(f"{email} logado")
        login_user(user)
        return redirect(next_page or url_for('main.home'))
    return render_template('auth/login.html')

@auth.route('/login/tenants/<int:tid>', methods=['GET', 'POST'])
def login_with_magic_link(tid):
    next_page = request.args.get('next')
    if current_user.is_authenticated:
        return redirect(next_page or url_for('main.home'))
    if not current_app.config["MAIL_USERNAME"] or not current_app.config["MAIL_PASSWORD"]:
        flash("O e-mail não está configurado", "warning")
        abort(404)
    if not (tenant := Tenant.query.get(tid)):
        abort(404)
    if not tenant.magic_link_login:
        flash("O recurso não está ativado", "warning")
        abort(404)
    if request.method == "POST":
        email = request.form["email"]
        if not (user := User.find_by_email(email)):
            flash(_l('E-mail inválido'), 'warning')
            Logs.add(f"e-mail inválido for {email}", level="warning")
            return redirect(url_for('auth.login_with_magic_link', tid=tid))
        if not user.is_active:
            flash(_l('O usuário está inativo'), 'warning')
            Logs.add(f"usuário inativo tentou fazer login:{email}", level="warning")
            return redirect(next_page or url_for('auth.login_with_magic_link', tid=tid))
        # send email with login
        token = user.generate_magic_link(tid)
        link = f"{current_app.config['HOST_NAME']}magic-login/{token}"
        title = f"{current_app.config['APP_NAME']}: Solicitação de login"
        content = f"Você solicitou um login por e-mail. Se você não solicitou um link mágico, ignore. Caso contrário, clique no botão abaixo para fazer login."
        send_email(
            title,
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[email],
            text_body=render_template(
                'email/basic_template.txt',
                title=title,
                content=content,
                button_link=link
            ),
            html_body=render_template(
                'email/basic_template.html',
                title=title,
                content=content,
                button_link=link,
                button_label="Login"
            )
        )
        Logs.add(f"solicitação de login do link mágico para {email}")
        flash("Verifique seu e-mail para obter as informações de login")
    return render_template('auth/magic-login.html', tid=tid)

@auth.route('/magic-login/<string:token>', methods=['GET'])
def validate_magic_link(token):
    next_page = request.args.get('next')
    if not (vtoken := User.verify_magic_token(token)):
        flash("O token é inválido", "warning")
        return redirect(url_for('auth.login'))
    if not (user := User.query.get(vtoken.get("user_id"))):
        flash("ID de usuário inválido", "warning")
        return redirect(url_for('auth.login'))
    if not (tenant := Tenant.query.get(vtoken.get("tenant_id"))):
        flash("ID de locatário inválido", "warning")
        return redirect(url_for('auth.login'))
    if user.id == tenant.owner_id or user.has_tenant(tenant):
        flash("Bem-Vindo")
        Logs.add(f"{user.email} logado via link mágico")
        login_user(user)
        return redirect(next_page or url_for('main.home'))
    flash("O usuário não consegue acessar o locatário", "warning")
    return redirect(url_for('auth.login'))

@auth.route('/logout')
def logout():
    logout_user()
    flash("Você está desconectado", "success")
    Logs.add(f"{current_user} logged out")
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    next_page = request.args.get('next')
    if current_user.is_authenticated:
        flash("Você já está registrado", "success")
        return redirect(next_page or url_for('main.home'))
    email = None
    result = {}
    if token := request.args.get("token"):
        if result := User.verify_invite_token(token):
            email = result["email"]
    if current_app.config["ENABLE_SELF_REGISTRATION"] != "1":
        if not token:
            Logs.add("faltando token para registro", level="warning")
            flash("Token ausente","warning")
            return redirect(url_for("auth.login"))
        if not result:
            Logs.add(f"token inválido ou expirado", level="warning")
            flash("Token inválido ou expirado","warning")
            return redirect(url_for("auth.login"))
    if request.method == "POST":
        email = email or request.form["email"]
        username = request.form.get("username")
        password = request.form.get("password")
        password2 = request.form.get("password2")
        if not User.validate_registration(email, username, password, password2):
            flash("E-mail, nome de usuário e/ou senha inválidos", "warning")
            return redirect(next_page or url_for('auth.register', token=token))
        new_user = User.add(email, password=password,
            username=username, confirmed=True,
            tenants=[{"id":result.get("tenant_id"), "roles": result.get("roles",[])}])
        login_user(new_user)
        flash(f'{email}, você agora está registrado', 'success')
        Logs.add(f"{email} registrado com sucesso")
        return redirect(next_page or url_for('main.home'))
    return render_template('auth/register.html', email=email)

@auth.route("/reset-password", methods=['GET', 'POST'])
def reset_password_request():
    next_page = request.args.get('next')
    internal = request.args.get('internal')
    if current_user.is_authenticated and not internal:
        return redirect(next_page or url_for('main.home'))
    if request.method == "POST":
        email = request.form.get("email")
        if not (user := User.find_by_email(email)):
            flash("E-mail enviado, verifique seu e-mail")
            return redirect(next_page or url_for('auth.reset_password_request'))
        Logs.add(f"{email} solicitou uma redefinição de senha", level="warning")
        token = user.generate_auth_token()
        link = f"{current_app.config['HOST_NAME']}reset-password/{token}"
        title = f"{current_app.config['APP_NAME']}: Redefinição de senha"
        content = f"Você solicitou uma redefinição de senha. Se não solicitou uma redefinição, ignore. Caso contrário, clique no botão abaixo para continuar."
        send_email(
            title,
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[email],
            text_body=render_template(
                'email/basic_template.txt',
                title=title,
                content=content,
                button_link=link
            ),
            html_body=render_template(
                'email/basic_template.html',
                title=title,
                content=content,
                button_link=link,
                button_label="Reset"
            )
        )
        flash("Email sent, check your mail")
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html')

@auth.route("/reset-password/<token>", methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if not (user := User.verify_auth_token(token)):
        Logs.add("token inválido ou ausente para redefinição de senha", level="warning")
        flash("Token ausente ou inválido","warning")
        return redirect(url_for("auth.reset_password_request"))
    if request.method == "POST":
        password = request.form.get("password")
        password2 = request.form.get("password2")
        if not misc.perform_pwd_checks(password, password_two=password2):
            flash("A senha não passou nas verificações", "warning")
            return redirect(url_for("auth.reset_password", token=token))
        user.set_password(password)
        db.session.commit()
        flash("Redefinição de senha! Por favor faça login com sua nova senha", "success")
        Logs.add(f"{user.email} redefinir sua senha", level="warning")
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html',token=token)
