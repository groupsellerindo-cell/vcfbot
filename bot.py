import os
import asyncio
import re
from threading import Thread
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, ForceReply

# --- CONFIGURATION (Environment Variables) ---
API_ID = int(os.getenv("API_ID", "0")) 
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# --- ADMIN SYSTEM ---
ADMIN_FILE = "admins.txt"

def get_admins():
    admins = {OWNER_ID}
    if os.path.exists(ADMIN_FILE):
        with open(ADMIN_FILE, "r") as f:
            for line in f:
                if line.strip().isdigit():
                    admins.add(int(line.strip()))
    return admins

def add_admin_to_file(user_id):
    with open(ADMIN_FILE, "a") as f: f.write(f"{user_id}\n")

def remove_admin_from_file(user_id):
    admins = get_admins()
    if user_id in admins:
        admins.remove(user_id)
        with open(ADMIN_FILE, "w") as f:
            for admin in admins:
                if admin != OWNER_ID: f.write(f"{admin}\n")
    return admins

ADMINS = get_admins()

# --- APP SETUP ---
if not BOT_TOKEN:
    print("Error: BOT_TOKEN variable not found!")
    exit()

app = Client("fast_contact_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- STATE MANAGEMENT ---
user_data = {}

# States
S_NONE = 0
S_COLLECTING_T2V = 1
S_T2V_CONTACT_NAME = 2
S_T2V_FILE_MODE = 3
S_T2V_CUSTOM_NAME = 4
S_COLLECTING_V2T = 5
S_V2T_MODE = 6
S_V2T_CUSTOM = 7
S_COLLECTING_RENAME = 8
S_RENAME_MODE = 9
S_RENAME_CUSTOM = 10
S_MSG_INPUT = 11
S_MSG_FILENAME = 12
S_SPLIT_FILE = 13
S_SPLIT_COUNT = 14
S_SPLIT_MODE = 15
S_SPLIT_CUSTOM = 16
S_NAVY_TEXT = 17
S_NAVY_FILENAME = 18
S_COLLECTING_REN_CTC = 19
S_REN_CTC_NAME = 20
S_REN_CTC_MODE = 21
S_REN_CTC_CUSTOM = 22
S_COLLECTING_MERGE_VCF = 23
S_MERGE_VCF_MODE = 24
S_MERGE_VCF_CUSTOM = 25
S_COLLECTING_MERGE_TXT = 26
S_MERGE_TXT_MODE = 27
S_MERGE_TXT_CUSTOM = 28

# --- HELPER FUNCTIONS ---
def is_admin(user_id):
    return user_id in ADMINS

async def reset_user(user_id):
    if user_id in user_data:
        if 'files' in user_data[user_id]:
            for f in user_data[user_id]['files']:
                if os.path.exists(f): os.remove(f)
        del user_data[user_id]

def clean_contact_name(name):
    return re.sub(r'\s*\d+$', '', name).strip()

# --- KEYBOARDS ---
DONE_BTN = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Upload Done / Next", callback_data="done_batch")]])
NAME_MODE_BTN = InlineKeyboardMarkup([
    [InlineKeyboardButton("📂 Default Name", callback_data="name_default")],
    [InlineKeyboardButton("✏️ Custom Name", callback_data="name_custom")]
])

# --- COMMANDS ---

@app.on_message(filters.command("start"))
async def start(client, message):
    if not is_admin(message.from_user.id): return
    await message.reply(
        "⚡ **Professional Batch Bot Ready**\n\n"
        "**Available Tools:**\n"
        "➤ **/txt_to_vcf** - Text to VCF (Sequential)\n"
        "➤ **/vcf_to_txt** - VCF to Text\n"
        "➤ **/msg_to_txt** - Message to File\n"
        "➤ **/rename_file** - Bulk Rename Files\n"
        "➤ **/rename_ctc** - Rename Contact Name (Sequential)\n"
        "➤ **/merge_vcf** - Merge Multiple VCFs\n"
        "➤ **/merge_txt** - Merge Multiple TXTs\n"
        "➤ **/split_file** - Split Big Files\n"
        "➤ **/admin_navy_file** - Admin Format\n"
        "➤ **/reset** - Cancel Process"
    )

@app.on_message(filters.command("reset"))
async def reset(client, message):
    await reset_user(message.from_user.id)
    await message.reply("🔄 **Process Reset Successfully.**")

# --- ADMIN COMMANDS ---
@app.on_message(filters.command("addadmin") & filters.user(OWNER_ID))
async def add_adm(c, m):
    if len(m.command) > 1:
        try:
            uid = int(m.command[1])
            add_admin_to_file(uid)
            ADMINS.add(uid)
            await m.reply(f"✅ **User {uid} added as Admin.**")
        except: pass

@app.on_message(filters.command("deladmin") & filters.user(OWNER_ID))
async def del_adm(c, m):
    if len(m.command) > 1:
        try:
            uid = int(m.command[1])
            if uid in ADMINS:
                ADMINS.remove(uid)
                remove_admin_from_file(uid)
                await m.reply(f"🗑️ **User {uid} removed from Admin.**")
        except: pass

# --- HANDLERS ---

@app.on_message(filters.command("txt_to_vcf"))
async def t2v_start(c, m):
    if not is_admin(m.from_user.id): return
    uid = m.from_user.id
    user_data[uid] = {'state': S_COLLECTING_T2V, 'files': [], 'original_names': []}
    await m.reply("📂 **Send Text Files.**\nAuto-delete enabled. Click Done when finished.", reply_markup=DONE_BTN)

@app.on_message(filters.command("rename_ctc"))
async def ren_ctc_start(c, m):
    if not is_admin(m.from_user.id): return
    uid = m.from_user.id
    user_data[uid] = {'state': S_COLLECTING_REN_CTC, 'files': [], 'original_names': []}
    await m.reply("📂 **Send VCF Files to Rename Contacts.**\n(Sequence: Name 1, Name 2...)\nClick Done when finished.", reply_markup=DONE_BTN)

@app.on_message(filters.command("vcf_to_txt"))
async def v2t_start(c, m):
    if not is_admin(m.from_user.id): return
    uid = m.from_user.id
    user_data[uid] = {'state': S_COLLECTING_V2T, 'files': [], 'original_names': []}
    await m.reply("📂 **Send VCF Files.**\nClick Done when finished.", reply_markup=DONE_BTN)

@app.on_message(filters.command("rename_file"))
async def ren_start(c, m):
    if not is_admin(m.from_user.id): return
    uid = m.from_user.id
    user_data[uid] = {'state': S_COLLECTING_RENAME, 'files': [], 'exts': [], 'original_names': []}
    await m.reply("📂 **Send Files to Rename.**\nClick Done when finished.", reply_markup=DONE_BTN)

@app.on_message(filters.command("merge_vcf"))
async def merge_vcf_start(c, m):
    if not is_admin(m.from_user.id): return
    uid = m.from_user.id
    user_data[uid] = {'state': S_COLLECTING_MERGE_VCF, 'files': []}
    await m.reply("📂 **Send VCF Files to Merge.**\nClick Done when finished.", reply_markup=DONE_BTN)

@app.on_message(filters.command("merge_txt"))
async def merge_txt_start(c, m):
    if not is_admin(m.from_user.id): return
    uid = m.from_user.id
    user_data[uid] = {'state': S_COLLECTING_MERGE_TXT, 'files': []}
    await m.reply("📂 **Send Text Files to Merge.**\nClick Done when finished.", reply_markup=DONE_BTN)

@app.on_message(filters.command("msg_to_txt"))
async def m2t_start(c, m):
    if not is_admin(m.from_user.id): return
    user_data[m.from_user.id] = {'state': S_MSG_INPUT}
    await m.reply("📝 **Type your message content below:**", reply_markup=ForceReply(True))

@app.on_message(filters.command("split_file"))
async def split_start(c, m):
    if not is_admin(m.from_user.id): return
    user_data[m.from_user.id] = {'state': S_SPLIT_FILE}
    await m.reply("✂️ **Send the File you want to split:**")

@app.on_message(filters.command("admin_navy_file"))
async def navy_start(c, m):
    if not is_admin(m.from_user.id): return
    user_data[m.from_user.id] = {'state': S_NAVY_TEXT}
    await m.reply("📝 **Send Data in Admin/Navy Format:**", reply_markup=ForceReply(True))

# --- FILE COLLECTOR ---
@app.on_message(filters.document)
async def handle_docs(c, m):
    uid = m.from_user.id
    if uid not in user_data: return
    st = user_data[uid].get('state')

    if st in [S_COLLECTING_T2V, S_COLLECTING_V2T, S_COLLECTING_RENAME, S_COLLECTING_REN_CTC]:
        path = await m.download()
        user_data[uid]['files'].append(path)
        base, ext = os.path.splitext(m.document.file_name)
        user_data[uid]['original_names'].append(base)
        if st == S_COLLECTING_RENAME: user_data[uid]['exts'].append(ext)
        try: await m.delete()
        except: pass

    elif st in [S_COLLECTING_MERGE_VCF, S_COLLECTING_MERGE_TXT]:
        path = await m.download()
        user_data[uid]['files'].append(path)
        try: await m.delete()
        except: pass

    elif st == S_SPLIT_FILE:
        msg = await m.reply("🔄 **Analyzing File...**")
        path = await m.download()
        base, ext = os.path.splitext(m.document.file_name)
        try: await m.delete()
        except: pass
        
        is_vcf = path.endswith(".vcf")
        count = 0
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            count = content.count("BEGIN:VCARD") if is_vcf else len(content.splitlines())
        
        user_data[uid].update({'state': S_SPLIT_COUNT, 'path': path, 'is_vcf': is_vcf, 'total_items': count, 'original_name': base})
        try: await msg.delete() 
        except: pass
        await m.reply(f"📊 **Analysis Complete.**\n\n**Total Numbers:** `{count}`\n\n🔢 **Enter how many per file?**")

# --- CALLBACKS ---
@app.on_callback_query()
async def cb_handler(c, q):
    uid = q.from_user.id
    if uid not in user_data: return await q.answer("Session expired.")
    st = user_data[uid].get('state')
    data = q.data

    if data == "done_batch":
        if st in [S_COLLECTING_T2V, S_COLLECTING_V2T, S_COLLECTING_RENAME, S_COLLECTING_REN_CTC, S_COLLECTING_MERGE_VCF, S_COLLECTING_MERGE_TXT]:
             if not user_data[uid]['files']: return await q.answer("❌ No files!", show_alert=True)

        if st == S_COLLECTING_T2V:
            user_data[uid]['state'] = S_T2V_CONTACT_NAME
            await q.message.edit(f"✅ **Files Received.**\n\n👤 **Enter Contact Name Base:**\n(e.g., if you type 'Flame', contacts will be Flame 1, Flame 2...)")
        elif st == S_COLLECTING_V2T:
            user_data[uid]['state'] = S_V2T_MODE
            await q.message.edit("📝 **Select Output File Name Mode:**", reply_markup=NAME_MODE_BTN)
        elif st == S_COLLECTING_RENAME:
            user_data[uid]['state'] = S_RENAME_MODE
            await q.message.edit("📝 **Select Renaming Mode:**", reply_markup=NAME_MODE_BTN)
        elif st == S_COLLECTING_REN_CTC:
            user_data[uid]['state'] = S_REN_CTC_NAME
            await q.message.edit(f"✅ **Files Received.**\n\n👤 **Enter New Contact Name Base:**\n(Contacts will become Name 1, Name 2...)")
        elif st == S_COLLECTING_MERGE_VCF:
            user_data[uid]['state'] = S_MERGE_VCF_MODE
            await q.message.edit("📝 **Select Merged File Name Mode:**", reply_markup=NAME_MODE_BTN)
        elif st == S_COLLECTING_MERGE_TXT:
            user_data[uid]['state'] = S_MERGE_TXT_MODE
            await q.message.edit("📝 **Select Merged File Name Mode:**", reply_markup=NAME_MODE_BTN)

    elif data == "name_default":
        if st == S_T2V_FILE_MODE: await process_t2v(c, q.message, uid, False)
        elif st == S_V2T_MODE:    await process_v2t(c, q.message, uid, False)
        elif st == S_RENAME_MODE: await process_rename(c, q.message, uid, False)
        elif st == S_SPLIT_MODE:  await process_split(c, q.message, uid, False)
        elif st == S_REN_CTC_MODE: await process_ren_ctc(c, q.message, uid, False)
        elif st == S_MERGE_VCF_MODE: await process_merge(c, q.message, uid, False, ".vcf")
        elif st == S_MERGE_TXT_MODE: await process_merge(c, q.message, uid, False, ".txt")

    elif data == "name_custom":
        msg_text = "✏️ **Enter Custom File Name:**"
        if st == S_T2V_FILE_MODE: user_data[uid]['state'] = S_T2V_CUSTOM_NAME; await q.message.edit(msg_text)
        elif st == S_V2T_MODE: user_data[uid]['state'] = S_V2T_CUSTOM; await q.message.edit(msg_text)
        elif st == S_RENAME_MODE: user_data[uid]['state'] = S_RENAME_CUSTOM; await q.message.edit(msg_text)
        elif st == S_SPLIT_MODE: user_data[uid]['state'] = S_SPLIT_CUSTOM; await q.message.edit(msg_text)
        elif st == S_REN_CTC_MODE: user_data[uid]['state'] = S_REN_CTC_CUSTOM; await q.message.edit(msg_text)
        elif st == S_MERGE_VCF_MODE: user_data[uid]['state'] = S_MERGE_VCF_CUSTOM; await q.message.edit(msg_text)
        elif st == S_MERGE_TXT_MODE: user_data[uid]['state'] = S_MERGE_TXT_CUSTOM; await q.message.edit(msg_text)

# --- TEXT HANDLER ---
@app.on_message(filters.text)
async def text_handler(c, m):
    uid = m.from_user.id
    if uid not in user_data: return
    st = user_data[uid].get('state')

    if st == S_T2V_CONTACT_NAME:
        raw_name = m.text
        user_data[uid]['c_name'] = clean_contact_name(raw_name)
        user_data[uid]['state'] = S_T2V_FILE_MODE
        await m.reply(f"📝 **Base Name Set:** `{user_data[uid]['c_name']}`\nContacts will be {user_data[uid]['c_name']} 1, {user_data[uid]['c_name']} 2...\n\n**Select Output File Name Mode:**", reply_markup=NAME_MODE_BTN)
    
    elif st == S_REN_CTC_NAME:
        raw_name = m.text
        user_data[uid]['c_name'] = clean_contact_name(raw_name)
        user_data[uid]['state'] = S_REN_CTC_MODE
        await m.reply(f"📝 **Base Name Set:** `{user_data[uid]['c_name']}`\n\n**Select Output File Name Mode:**", reply_markup=NAME_MODE_BTN)

    elif st == S_T2V_CUSTOM_NAME:
        user_data[uid]['custom_name'] = m.text; await process_t2v(c, m, uid, True)
    elif st == S_V2T_CUSTOM:
        user_data[uid]['custom_name'] = m.text; await process_v2t(c, m, uid, True)
    elif st == S_RENAME_CUSTOM:
        user_data[uid]['custom_name'] = m.text; await process_rename(c, m, uid, True)
    elif st == S_REN_CTC_CUSTOM:
        user_data[uid]['custom_name'] = m.text; await process_ren_ctc(c, m, uid, True)
    elif st == S_MERGE_VCF_CUSTOM:
        user_data[uid]['custom_name'] = m.text; await process_merge(c, m, uid, True, ".vcf")
    elif st == S_MERGE_TXT_CUSTOM:
        user_data[uid]['custom_name'] = m.text; await process_merge(c, m, uid, True, ".txt")

    elif st == S_MSG_INPUT:
        user_data[uid]['msg_content'] = m.text
        user_data[uid]['state'] = S_MSG_FILENAME
        await m.reply("📝 **Enter File Name:**")
    elif st == S_MSG_FILENAME:
        fname = m.text.strip()
        if not fname.endswith(".txt"): fname += ".txt"
        
        msg_content = user_data[uid]['msg_content']
        new_content = ""
        for line in msg_content.splitlines():
            line = line.strip()
            if line.replace('+', '').isdigit():
                new_content += "+" + line.replace('+', '') + "\n"
            else:
                new_content += line + "\n"

        with open(fname, 'w', encoding='utf-8') as f: f.write(new_content)
        await m.reply_document(fname)
        await m.reply("✅ **Done!**")
        os.remove(fname)
        await reset_user(uid)
        
    elif st == S_SPLIT_COUNT:
        try:
            count = int(m.text)
            user_data[uid]['split_count'] = count
            user_data[uid]['state'] = S_SPLIT_MODE
            await m.reply("📝 **Select Output File Name Mode:**", reply_markup=NAME_MODE_BTN)
        except: await m.reply("❌ **Please enter a valid number.**")
    elif st == S_SPLIT_CUSTOM:
        user_data[uid]['custom_name'] = m.text
        await process_split(c, m, uid, True)
    
    elif st == S_NAVY_TEXT:
        user_data[uid]['text'] = m.text
        user_data[uid]['state'] = S_NAVY_FILENAME
        await m.reply("📝 **Enter Output File Name:**")
    elif st == S_NAVY_FILENAME:
        fname = m.text.strip() + ".vcf"
        raw = user_data[uid]['text']
        vcf, tn = "", None
        for l in raw.splitlines():
            l=l.strip()
            if not l: continue
            if l.replace('+','').isdigit() and len(l)>5:
                if tn:
                    clean_num = "+" + l.replace('+', '')
                    vcf+=f"BEGIN:VCARD\nVERSION:3.0\nFN:{tn}\nTEL;TYPE=CELL:{clean_num}\nEND:VCARD\n"
                    tn=None
            else: tn=l
        with open(fname,'w',encoding='utf-8') as f: f.write(vcf)
        await m.reply_document(fname)
        await m.reply("✅ **Done!**")
        os.remove(fname)
        await reset_user(uid)

# --- PROCESSORS ---

async def process_t2v(c, m, uid, custom):
    proc_msg = await m.reply("⚙️ **Processing with Sequential Names & Plus Sign...**")
    try:
        files = user_data[uid]['files']
        c_name_base = user_data[uid]['c_name']
        
        for i, path in enumerate(files):
            out_name = f"{user_data[uid].get('custom_name')} {i+1}.vcf" if custom else f"{user_data[uid]['original_names'][i]}.vcf"
            
            with open(path, 'r', encoding='utf-8', errors='ignore') as f: lines = f.readlines()
            data = ""
            
            counter = 1
            for num in lines:
                num = num.strip()
                if num: 
                    clean_num = "+" + num.replace('+', '')
                    data += f"BEGIN:VCARD\nVERSION:3.0\nFN:{c_name_base} {counter}\nTEL;TYPE=CELL:{clean_num}\nEND:VCARD\n"
                    counter += 1
            
            with open(out_name, 'w', encoding='utf-8') as f: f.write(data)
            await m.reply_document(out_name)
            
            if i == 0:
                try: await proc_msg.delete()
                except: pass
            
            os.remove(out_name)
            os.remove(path)
            
        await m.reply("✅ **All Files Done.**")
    except Exception as e: await m.reply(f"❌ Error: {e}")
    await reset_user(uid)

async def process_ren_ctc(c, m, uid, custom):
    proc_msg = await m.reply("⚙️ **Renaming Contacts & Adding Plus Sign...**")
    files = user_data[uid]['files']
    new_c_name_base = user_data[uid]['c_name']
    
    try:
        for i, path in enumerate(files):
            out_name = f"{user_data[uid].get('custom_name')} {i+1}.vcf" if custom else f"{user_data[uid]['original_names'][i]}.vcf"
            
            new_content = ""
            counter = 1
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.startswith("FN:"):
                        new_content += f"FN:{new_c_name_base} {counter}\n"
                        counter += 1
                    elif "TEL" in line and ":" in line:
                        parts = line.split(":", 1)
                        clean_num = "+" + parts[1].strip().replace('+', '')
                        new_content += f"{parts[0]}:{clean_num}\n"
                    else:
                        new_content += line
            
            with open(out_name, 'w', encoding='utf-8') as f: f.write(new_content)
            await m.reply_document(out_name)
            
            if i == 0:
                try: await proc_msg.delete()
                except: pass
            
            os.remove(out_name)
            os.remove(path)
            
        await m.reply("✅ **All Files Done.**")
    except Exception as e: await m.reply(f"❌ Error: {e}")
    await reset_user(uid)

async def process_split(c, m, uid, custom):
    proc_msg = await m.reply("⚙️ **Splitting & Checking Plus Sign...**")
    try:
        path = user_data[uid]['path']
        limit = user_data[uid]['split_count']
        is_vcf = user_data[uid]['is_vcf']
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f: content = f.read()

        if is_vcf:
            content = re.sub(r'(TEL.*?:)\s*\+?(\d+)', r'\1+\2', content)
            items = [x+"END:VCARD\n" for x in content.strip().split("END:VCARD") if "BEGIN:VCARD" in x]
            ext = ".vcf"
        else:
            raw_items = content.splitlines()
            items = []
            for x in raw_items:
                x = x.strip()
                if x:
                    if x.replace('+', '').isdigit():
                        items.append("+" + x.replace('+', '') + "\n")
                    else:
                        items.append(x + "\n")
            ext = ".txt"

        total = (len(items)+limit-1)//limit
        for i in range(total):
            chunk = items[i*limit:(i+1)*limit]
            out_name = f"{user_data[uid].get('custom_name')} {i+1}{ext}" if custom else f"{user_data[uid]['original_name']} {i+1}{ext}"
            
            with open(out_name, 'w', encoding='utf-8') as f: f.writelines(chunk)
            await m.reply_document(out_name)
            
            if i == 0:
                try: await proc_msg.delete()
                except: pass
            
            os.remove(out_name)
        os.remove(path)
        await m.reply("✅ **All Files Done.**")
    except Exception as e: await m.reply(f"❌ Error: {e}")
    await reset_user(uid)

async def process_v2t(c, m, uid, custom):
    proc_msg = await m.reply("⚙️ **Processing & Adding Plus Sign...**")
    try:
        files = user_data[uid]['files']
        for i, path in enumerate(files):
            out_name = f"{user_data[uid].get('custom_name')} {i+1}.txt" if custom else f"{user_data[uid]['original_names'][i]}.txt"
            nums = []
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for l in f:
                    if "TEL" in l: 
                        raw_num = l.split(':')[-1].strip()
                        clean_num = "+" + raw_num.replace('+', '')
                        nums.append(clean_num)
            
            with open(out_name, 'w', encoding='utf-8') as f: f.write("\n".join(nums))
            await m.reply_document(out_name)
            
            if i == 0:
                try: await proc_msg.delete()
                except: pass
            
            os.remove(out_name)
            os.remove(path)
        await m.reply("✅ **All Files Done.**")
    except Exception as e: await m.reply(f"❌ Error: {e}")
    await reset_user(uid)

async def process_rename(c, m, uid, custom):
    proc_msg = await m.reply("⚙️ **Processing...**")
    try:
        files = user_data[uid]['files']
        for i, path in enumerate(files):
            ext = user_data[uid]['exts'][i]
            new_name = f"{user_data[uid].get('custom_name')} {i+1}{ext}" if custom else f"{user_data[uid]['original_names'][i]}{ext}"
            os.rename(path, new_name)
            await m.reply_document(new_name)
            
            if i == 0:
                try: await proc_msg.delete()
                except: pass
            
            os.remove(new_name)
        await m.reply("✅ **All Files Done.**")
    except Exception as e: await m.reply(f"❌ Error: {e}")
    await reset_user(uid)

async def process_merge(c, m, uid, custom, ext):
    proc_msg = await m.reply("⚙️ **Processing Merge & Checking Plus Sign...**")
    files = user_data[uid]['files']
    final_name = f"{user_data[uid].get('custom_name')}{ext}" if custom else f"Merged_Output{ext}"
    try:
        with open(final_name, 'w', encoding='utf-8') as outfile:
            for path in files:
                with open(path, 'r', encoding='utf-8', errors='ignore') as infile:
                    if ext == ".vcf":
                        content = infile.read()
                        content = re.sub(r'(TEL.*?:)\s*\+?(\d+)', r'\1+\2', content)
                        outfile.write(content)
                    else:
                        for line in infile:
                            line = line.strip()
                            if line:
                                if line.replace('+', '').isdigit():
                                    outfile.write("+" + line.replace('+', '') + "\n")
                                else:
                                    outfile.write(line + "\n")
                os.remove(path)
        
        try: await proc_msg.delete()
        except: pass
        
        await m.reply_document(final_name)
        await m.reply("✅ **Merge Done.**")
        os.remove(final_name)
    except Exception as e: await m.reply(f"❌ Error: {e}")
    await reset_user(uid)

# --- DUMMY WEB SERVER FOR RENDER ---
web_app = Flask(__name__)
@web_app.route('/')
def home():
    return "Bot is running on Render!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# Starting Flask in a separate thread
Thread(target=run_web).start()

print("🚀 Bot Started on Server (With Web Port)...")
app.run()
