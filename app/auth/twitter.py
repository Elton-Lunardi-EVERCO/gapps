from datetime import datetime as dt
from secrets import token_urlsafe
from flask import flash, redirect, url_for, current_app

from flask_babel import lazy_gettext as _l
from flask_login import login_user, current_user
from flask_dance.consumer.storage.sqla import SQLAlchemyStorage
from flask_dance.consumer import oauth_authorized, oauth_error
from flask_dance.contrib.twitter import make_twitter_blueprint
from sqlalchemy.orm.exc import NoResultFound

from app.utils.misc import get_random_password_string
from app import db
from app.models import OAuth, User

twitter_bp = make_twitter_blueprint(
    api_key=current_app.config['TWITTER_OAUTH_API_KEY'],
    api_secret=current_app.config['TWITTER_OAUTH_API_SECRET'],
    storage=SQLAlchemyStorage(OAuth, db.session, user=current_user),
)


@oauth_authorized.connect_via(twitter_bp)
def twitter_logged_in(blueprint, token):
    if not token:
        flash("Falha ao fazer login.", category="error")
        return redirect(url_for('main.index'))

    resp = blueprint.session.get("account/verify_credentials.json?include_email=true")
    if not resp.ok:
        msg = "Falha ao buscar informações do usuário."
        flash(msg, category="error")
        return redirect(url_for('main.index'))

    info = resp.json()
    user_id = info.get("id", None)
    query = OAuth.query.filter_by(
        provider=blueprint.name,
        provider_user_id=str(user_id))

    try:
        oauth = query.one()
    except NoResultFound:
        oauth = OAuth(
            provider=blueprint.name,
            provider_user_id=user_id,
            token=token)

    if oauth.user:
        user = oauth.user
    else:
        # Create a new local user account for this user
        username = info.get("name", "No name")
        email = info.get(
            "email",
            "Verifique o endereço de e-mail de solicitação dos usuários em seu aplicativo do Twitter"
        )
        user = User(
            username=username.lower(),
            email=email,
            created=dt.now(),
            token=token_urlsafe(),
            token_expiration=dt.now()
        )
        password_generated = get_random_password_string(10)
        user.set_password(password_generated)
        # Associate the new local user account with the OAuth token
        oauth.user = user
        db.session.add_all([user, oauth])
        db.session.commit()
        flash(_l("Conexão com o Twitter com sucesso"), 'success')
    login_user(user)
    return redirect(url_for('main.index'))


@oauth_error.connect_via(twitter_bp)
def twitter_error(blueprint, message, response):
    msg = (_l("{message} {response}")).format(
        message=message,
        response=response
    )
    flash(msg, 'warning')
    return redirect(url_for('auth.login'))
