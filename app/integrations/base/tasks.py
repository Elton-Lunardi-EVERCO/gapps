from app.utils.bg_worker import bg_app
from app.utils.misc import get_class_by_tablename
from app.utils.bg_helper import BgHelper
from app.integrations.utils.decorators import task
from app import db
from flask import current_app
from croniter import croniter
from datetime import datetime
import arrow
import os

@bg_app.periodic(cron="* * * * *")
@bg_app.task(name="scheduler", queue="scheduler")
async def scheduler(timestamp: int):
    Task = get_class_by_tablename("Task")
    tasks = Task.query.all()
    if not tasks:
        current_app.logger.debug("O banco de dados não contém nenhuma tarefa periódica... pulando")
        return True
    current_app.logger.debug(f"Encontrado {len(tasks)} tarefas periódicas")
    for task in tasks:
        if not task.disabled:
            now = datetime.now()
            if not task.last_run or now > task.not_before:
                current_app.logger.info(f"A tarefa está pronta para adiamento: {task.get_lock()}")
                await BgHelper().run_async_task(task)
                task.last_run = now
                task.not_before = croniter(task.cron, now).get_next(datetime)
                db.session.commit()
            else:
                current_app.logger.debug(f"Tarefas periódicas: {task.get_lock()} não está pronto... pulando")
        else:
            current_app.logger.debug(f"Tarefas periódicas: {task.get_lock()} está desativado... pulando")
    return True
