from sqlalchemy.orm import Session
from app.models.task import Task

def create_task(db: Session, url: str):
    task = Task(url=url)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

def update_task_result(db: Session, task_id: int, result: str):
    task = db.query(Task).get(task_id)
    if task:
        task.result = result
        task.status = "completed"
        db.commit()
        db.refresh(task)
    return task