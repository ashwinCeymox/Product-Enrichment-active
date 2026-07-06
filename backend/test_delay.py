from app.tasks.gen_images import generate_images_task
try:
    generate_images_task.delay("123")
    print("Success")
except Exception as e:
    print(f"Failed: {type(e).__name__}: {e}")
