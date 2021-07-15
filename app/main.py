from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime
import msmcauth
import requests
from typing import Optional

app = FastAPI(openapi_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class LoginInfo(BaseModel):
    username: str
    password: str

error_codes = {
    1: "Authentication failed due to an unknown server error. Please try again later.",
    2: "This Microsoft account doesn't have an Xbox account. Once you sign up for one (or log in through minecraft.net to create one), you can proceed with the login. This shouldn't happen if you have purchased Minecraft with a Microsoft account, as you would've already gone through the Xbox sign-up process.",
    3: "This Microsoft account is a child account and cannot proceed unless added to a family account by an adult.",
    4: "This Microsoft account does not own Minecraft.",
    5: "The SimpleAuth endpoint cannot authenticate Microsoft accounts with 2FA. Would you please disable 2FA to enable authentication with this account?",
    6: "Credentials error. Would you please check if you have entered your username and password correctly?",
    7: "Empty JSON provided.",
    8: "Remember to set header to Content-Type: application/json.",
    9: "Try to sign in to https://account.live.com/activity or https://account.xbox.com/profile from your browser. As this API is hosted in the United States, Microsoft may block authentication for users who do not live in the US due to Microsoft thinking that you are \"logging in from an unknown location.\"",
    10: "This API is currently overloaded. Please try again later."
}


@app.get("/auth", response_class=HTMLResponse)
async def index(request: Request):
    print(f"[{datetime.now()}] [INFO] Served deprecation notice to user.")
    return templates.TemplateResponse("notice.html", {"request": request})


@app.post("/simpleauth")
def simple_auth(login_info: LoginInfo):
    try:
        username = login_info.username
        password = login_info.password
        print(f"[{datetime.now()}] [INFO] Requesting token and authenticating with XBL...")
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
        raise HTTPException(status_code=400, error=error_codes[2])
    except msmcauth.ChildAccount:
        print(f"[{datetime.now()}] [ERROR] Code: 3")
        raise HTTPException(status_code=400, error=error_codes[3])
    except msmcauth.TwoFactorAccount:
        print(f"[{datetime.now()}] [ERROR] Code: 5")
        raise HTTPException(status_code=400, error=error_codes[5])
    except msmcauth.InvalidCredentials:
        print(f"[{datetime.now()}] [ERROR] Code: 6")
        raise HTTPException(status_code=400, error=error_codes[6])
    except msmcauth.LoginWithXboxFailed:
        print(f"[{datetime.now()}] [ERROR] Code: 10")
        raise HTTPException(status_code=400, error=error_codes[10])
    except Exception as err:
        err = str(err)
        if err == "Something went wrong. Status Code: 200":
            print(f"[{datetime.now()}] [ERROR] Code: 9")
            raise HTTPException(status_code=400, error=error_codes[9])
        else:
            print(f"[{datetime.now()}] [ERROR] Unknown error: {err}")
            raise HTTPException(status_code=400, error=error_codes[1])