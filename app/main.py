from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
import msmcauth
import requests
from typing import Optional

tags_metadata = [
    {
        "name": "auth",
        "description": "Serves deprecation notice to old buckshot users as older versions of buckshot uses an OAuth2 authentication endpoint that is no longer working.",
    },
    {
        "name": "simpleauth",
        "description": "Authenticates Microsoft accounts and retrieves a bearer token for interfacing with Mojang APIs for Minecraft.",
    },
]

app = FastAPI(title="SimpleAuth",
    description="This API authenticates Microsoft accounts and retrieves a bearer token for interfacing with Mojang APIs for Minecraft.",
    version="1.0.0", docs_url=None, redoc_url="/", openapi_tags=tags_metadata)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


class LoginInfo(BaseModel):
    username: str
    password: str


error_codes = {
    1: "Authentication failed due to an unknown server error. Please try again later.",
    2: "This Microsoft account doesn't have an Xbox account. Once you sign up for one (or log in through minecraft.net to create one), you can proceed with the login. This shouldn't happen if you have purchased Minecraft with a Microsoft account, as you would've already gone through the Xbox sign-up process.",
    3: "This Microsoft account is a child account and cannot proceed unless added to a family account by an adult.",
    4: "The SimpleAuth endpoint cannot authenticate Microsoft accounts with 2FA. Would you please disable 2FA to enable authentication with this account?",
    5: "Credentials error. Would you please check if you have entered your username and password correctly?",
    6: "Try to sign in to https://account.live.com/activity or https://account.xbox.com/profile from your browser. As this API is hosted in the United States, Microsoft may block authentication for users who do not live in the US due to Microsoft thinking that you are 'logging in from an unknown location.'",
    7: "This API is currently overloaded. Please try again later."
}


@app.get("/auth", response_class=HTMLResponse, tags=["auth"])
async def index(request: Request):
    print(f"[{datetime.now()}] [INFO] Served deprecation notice to user.")
    return templates.TemplateResponse("notice.html", {"request": request})


@app.post("/simpleauth", tags=["simpleauth"])
def simple_auth(login_info: LoginInfo):
    try:
        username = login_info.username
        password = login_info.password
        print(
            f"[{datetime.now()}] [INFO] Requesting token and authenticating with XBL...")
        client = requests.Session()
        xbx = msmcauth.XboxLive(client)
        mic = msmcauth.Microsoft(client)
        res = xbx.user_login(username, password, xbx.pre_auth())
        xbl = mic.xbl_authenticate(res)
        xsts = mic.xsts_authenticate(xbl)
        access_token = mic.login_with_xbox(xsts.token, xsts.user_hash)
        print(f"[{datetime.now()}] [INFO] Successfully authenticated user.")
        return {"access_token": access_token}
    except msmcauth.NoXboxAccount:
        print(f"[{datetime.now()}] [ERROR] Code: 2")
        return JSONResponse(status_code=400, content={"error": error_codes[2]})
    except msmcauth.ChildAccount:
        print(f"[{datetime.now()}] [ERROR] Code: 3")
        return JSONResponse(status_code=400, content={"error": error_codes[3]})
    except msmcauth.TwoFactorAccount:
        print(f"[{datetime.now()}] [ERROR] Code: 4")
        return JSONResponse(status_code=400, content={"error": error_codes[4]})
    except msmcauth.InvalidCredentials:
        print(f"[{datetime.now()}] [ERROR] Code: 5")
        return JSONResponse(status_code=400, content={"error": error_codes[5]})
    except msmcauth.LoginWithXboxFailed:
        print(f"[{datetime.now()}] [ERROR] Code: 7")
        return JSONResponse(status_code=400, content={"error": error_codes[7]})
    except Exception as err:
        err = str(err)
        if err == "Something went wrong. Status Code: 200":
            print(f"[{datetime.now()}] [ERROR] Code: 6")
            return JSONResponse(status_code=400, content={"error": error_codes[6]})
        else:
            print(f"[{datetime.now()}] [ERROR] Unknown error: {err}")
            return JSONResponse(status_code=400, content={"error": error_codes[1]})
