import hashlib

import pandas as pd
import streamlit as st
from i18n import tr

from agro_utils import load_users, now_iso, save_users
from styles import apply_styles

apply_styles()

st.title(tr("module_users_access"))
st.caption("Local multi-user access with roles: admin, agronomist, viewer.")

ROLE_OPTIONS = ["admin", "agronomist", "viewer"]


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def ensure_default_admin():
    users = load_users()
    if users:
        return users
    users = [
        {
            "username": "admin",
            "password_hash": hash_password("admin123"),
            "role": "admin",
            "active": True,
            "created_at": now_iso(),
        }
    ]
    save_users(users)
    return users


def find_user(users, username):
    for u in users:
        if str(u.get("username")) == str(username):
            return u
    return None


users = ensure_default_admin()

if "auth_user" not in st.session_state:
    st.session_state["auth_user"] = None
if "auth_role" not in st.session_state:
    st.session_state["auth_role"] = "guest"

left, right = st.columns(2)
with left:
    if st.session_state["auth_user"] is None:
        with st.form("login_form"):
            st.subheader("Login")
            login = st.text_input("Username")
            password = st.text_input("Password", type="password")
            ok = st.form_submit_button("Sign in")

        if ok:
            user = find_user(users, login.strip())
            if not user:
                st.error("User not found.")
            elif not bool(user.get("active", True)):
                st.error("User is disabled.")
            elif user.get("password_hash") != hash_password(password):
                st.error("Wrong password.")
            else:
                st.session_state["auth_user"] = user["username"]
                st.session_state["auth_role"] = user.get("role", "viewer")
                st.success("Signed in.")
                st.rerun()
    else:
        st.subheader("Current session")
        st.write(f"User: **{st.session_state['auth_user']}**")
        st.write(f"Role: **{st.session_state['auth_role']}**")
        if st.button("Logout"):
            st.session_state["auth_user"] = None
            st.session_state["auth_role"] = "guest"
            st.rerun()

with right:
    st.subheader("Role permissions")
    matrix = pd.DataFrame(
        [
            {"role": "admin", "permissions": "all modules + user management"},
            {"role": "agronomist", "permissions": "field ops, NDVI, economics, nutrition, reports"},
            {"role": "viewer", "permissions": "read-only analytics and reports"},
        ]
    )
    st.dataframe(matrix, use_container_width=True, hide_index=True)

st.info("Default admin credentials (change immediately): admin / admin123")

if st.session_state["auth_role"] != "admin":
    st.warning("Only admin can manage accounts.")
    st.stop()

st.subheader("Create user")
with st.form("create_user", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        new_user = st.text_input("Username")
    with c2:
        new_pass = st.text_input("Password", type="password")
    with c3:
        new_role = st.selectbox("Role", ROLE_OPTIONS, index=1)
    create_ok = st.form_submit_button("Create")

if create_ok:
    username = new_user.strip()
    if not username or not new_pass:
        st.error("Username and password are required.")
    elif find_user(users, username):
        st.error("User already exists.")
    else:
        users.append(
            {
                "username": username,
                "password_hash": hash_password(new_pass),
                "role": new_role,
                "active": True,
                "created_at": now_iso(),
            }
        )
        save_users(users)
        st.success(f"User '{username}' created.")
        st.rerun()

if users:
    st.subheader("Manage existing users")
    usernames = [u.get("username") for u in users]
    sel = st.selectbox("Select user", usernames)
    u = find_user(users, sel)

    e1, e2 = st.columns(2)
    with e1:
        edit_role = st.selectbox("Role", ROLE_OPTIONS, index=ROLE_OPTIONS.index(u.get("role", "viewer")), key="edit_role")
    with e2:
        edit_active = st.checkbox("Active", value=bool(u.get("active", True)), key="edit_active")

    reset_password = st.text_input("Reset password (optional)", type="password")

    b1, b2 = st.columns(2)
    if b1.button("Save changes"):
        u["role"] = edit_role
        u["active"] = edit_active
        if reset_password:
            u["password_hash"] = hash_password(reset_password)
        save_users(users)
        st.success("User updated.")
        st.rerun()

    if b2.button("Delete user"):
        if sel == "admin":
            st.error("Cannot delete default admin user.")
        else:
            users = [x for x in users if x.get("username") != sel]
            save_users(users)
            st.success("User deleted.")
            st.rerun()

    show = pd.DataFrame(users)
    if "password_hash" in show.columns:
        show["password_hash"] = show["password_hash"].str.slice(0, 10) + "..."
    st.dataframe(show, use_container_width=True, hide_index=True)
