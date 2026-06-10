from fastapi.responses import JSONResponse


def success(data=None, message="ok"):
    """成功响应"""
    return {"code": 0, "data": data, "message": message}


def error(message="error", code=1, data=None):
    """错误响应"""
    return {"code": code, "data": data, "message": message}
