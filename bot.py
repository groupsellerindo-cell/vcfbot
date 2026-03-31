import os
import re
import vobject
import logging
import time
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler
)

# --- CONFIG & SECURITY ---
TOKEN = os.getenv("BOT_TOKEN")
# Agar OWNER_ID render par set nahi hai toh crash se bachne ke liye 0 default kiya hai
OWNER_ID = int(os.getenv("OWNER_ID", "0")) 
ADMINS = [OWNER_ID]

# States for ConversationHandler
(TXT_TO_VCF_FILE, TXT_TO_VCF_NAME, TXT_TO_VCF_VCFNAME, 
 VCF_TO_TXT_FILE, VCF_TO_TXT_NAME, MSG_TO_TXT_PROC, 
 RENAME_C_FILE, RENAME_C_NAME, RENAME_F_PROC, 
 SPLIT_PROC_FILE, SPLIT_PROC_NUM, ADMIN_NAVY_PROC) = range(12)

# --- WEB SERVER (For 24/7 on Render) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Running 24/7!"

def run():
    # Render requires binding to the $PORT env variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- HELPER: VCF Generator ---
def generate_vcf(numbers, contact_name, output_name, start_idx=1):
    path = f"{output_name}.vcf"
    with open(path, "w", encoding="utf-8") as f:
        for i, num in enumerate(numbers):
            f.write("BEGIN:VCARD\nVERSION:3.0\n")
            f.write(f"FN:{contact_name} {i + start_idx}\n")
            f.write(f"TEL;TYPE=CELL:{num}\n")
            f.write("END:VCARD\n")
    return path

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    msg = (
        "🚀 *Fast VCF Manager Pro*\n\n"
        "*/t2v* - Text to VCF\n"
        "*/v2t* - VCF to Text\n"
        "*/m2t* - Message to Text\n"
        "*/r_c* - Rename Contact Name\n"
        "*/r_f* - Rename File (Bulk)\n"
        "*/split* - Split Files\n"
        "*/navy* - Admin Navy Format\n"
        "*/reset* - Cancel Process"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🔄 Process Reset.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- 1. TEXT TO VCF ---
async def t2v_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📁 Send the `.txt` file.")
    return TXT_TO_VCF_FILE

async def t2v_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    path = f"downloads/{update.message.document.file_name}"
    await file.download_to_drive(path)
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        context.user_data['numbers'] = re.findall(r'\d+', f.read())
    await update.message.reply_text("👤 Enter Contact Name:")
    return TXT_TO_VCF_NAME

async def t2v_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['c_name'] = update.message.text
    await update.message.reply_text("📄 Enter Output File Name:")
    return TXT_TO_VCF_VCFNAME

async def t2v_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vcf = generate_vcf(context.user_data['numbers'], context.user_data['c_name'], update.message.text)
    await update.message.reply_document(document=open(vcf, 'rb'))
    os.remove(vcf)
    return ConversationHandler.END

# --- 2. VCF TO TEXT ---
async def v2t_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📁 Send VCF file.")
    return VCF_TO_TXT_FILE

async def v2t_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    path = f"downloads/{update.message.document.file_name}"
    await file.download_to_drive(path)
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        nums = re.findall(r'TEL;.*?:(\d+)', f.read())
    context.user_data['numbers'] = nums
    await update.message.reply_text("📄 Enter Text File Name:")
    return VCF_TO_TXT_NAME

async def v2t_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fname = f"{update.message.text}.txt"
    with open(fname, "w") as f:
        f.write("\n".join(context.user_data['numbers']))
    await update.message.reply_document(document=open(fname, 'rb'))
    os.remove(fname)
    return ConversationHandler.END

# --- 3. MESSAGE TO TEXT ---
async def m2t_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send message with numbers.")
    return MSG_TO_TXT_PROC

async def m2t_proc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nums = re.findall(r'\d+', update.message.text)
    fname = "numbers.txt"
    with open(fname, "w") as f:
        f.write("\n".join(nums))
    await update.message.reply_document(document=open(fname, 'rb'))
    os.remove(fname)
    return ConversationHandler.END

# --- 4. RENAME CONTACT NAME (VCF) ---
async def rc_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send VCF file to rename contacts.")
    return RENAME_C_FILE

async def rc_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    path = f"downloads/{update.message.document.file_name}"
    await file.download_to_drive(path)
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        nums = re.findall(r'TEL;.*?:(\d+)', f.read())
    context.user_data['numbers'] = nums
    await update.message.reply_text(f"Found {len(nums)} contacts. Enter New Name:")
    return RENAME_C_NAME

async def rc_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vcf = generate_vcf(context.user_data['numbers'], update.message.text, "Renamed_Contacts")
    await update.message.reply_document(document=open(vcf, 'rb'))
    os.remove(vcf)
    return ConversationHandler.END

# --- 5. BULK RENAME FILE ---
async def rf_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send file(s). Use /reset when done.")
    return RENAME_F_PROC

async def rf_proc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        doc = update.message.document
        await update.message.reply_text(f"Renaming {doc.file_name}. Enter new name:")
        context.user_data['current_file'] = doc
        return RENAME_F_PROC
    else:
        doc = context.user_data.get('current_file')
        ext = os.path.splitext(doc.file_name)[1]
        new_name = f"{update.message.text}{ext}"
        file = await doc.get_file()
        await file.download_to_drive(new_name)
        await update.message.reply_document(document=open(new_name, 'rb'))
        os.remove(new_name)
        await update.message.reply_text("Done! Send another or /reset.")
        return RENAME_F_PROC

# --- 6. SPLIT MEMBERS ---
async def split_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send VCF or Text file.")
    return SPLIT_PROC_FILE

async def split_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    path = f"downloads/{doc.file_name}"
    file = await doc.get_file()
    await file.download_to_drive(path)
    
    if path.endswith('.vcf'):
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = re.findall(r'BEGIN:VCARD.*?END:VCARD', f.read(), re.S)
    else:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
    context.user_data['lines'] = lines
    context.user_data['ext'] = "vcf" if path.endswith('.vcf') else "txt"
    await update.message.reply_text(f"Total: {len(lines)}. Per file limit?")
    return SPLIT_PROC_NUM

async def split_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        limit = int(update.message.text)
        lines = context.user_data['lines']
        ext = context.user_data['ext']
        for i in range(0, len(lines), limit):
            chunk = lines[i:i + limit]
            fname = f"Part_{i//limit + 1}.{ext}"
            with open(fname, 'w', encoding='utf-8') as f:
                if ext == 'vcf': f.write("\n".join(chunk))
                else: f.writelines(chunk)
            await update.message.reply_document(document=open(fname, 'rb'))
            os.remove(fname)
        return ConversationHandler.END
    except:
        await update.message.reply_text("Invalid number.")

# --- 8. ADMIN NAVY ---
async def navy_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send list (Admin/Navy format):")
    return ADMIN_NAVY_PROC

async def navy_proc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = update.message.text.split('\n')
    vcf_str, curr_name = "", "Contact"
    for line in lines:
        line = line.strip().replace("+", "")
        if not line: continue
        if line.isdigit():
            vcf_str += f"BEGIN:VCARD\nVERSION:3.0\nFN:{curr_name}\nTEL;TYPE=CELL:{line}\nEND:VCARD\n"
        else: curr_name = line
    with open("Navy.vcf", "w", encoding='utf-8') as f: f.write(vcf_str)
    await update.message.reply_document(document=open("Navy.vcf", 'rb'))
    os.remove("Navy.vcf")
    return ConversationHandler.END

# --- MAIN ---
def main():
    if not os.path.exists("downloads"): os.makedirs("downloads")
    
    # Keep Alive server ko pehle start karo aur thoda wait karo
    keep_alive()
    time.sleep(1) # Isse Flask pehle port bind kar lega
    
    app_tg = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler('t2v', t2v_start),
            CommandHandler('v2t', v2t_start),
            CommandHandler('m2t', m2t_start),
            CommandHandler('r_c', rc_start),
            CommandHandler('r_f', rf_start),
            CommandHandler('split', split_start),
            CommandHandler('navy', navy_start)
        ],
        states={
            TXT_TO_VCF_FILE: [MessageHandler(filters.Document.ALL, t2v_file)],
            TXT_TO_VCF_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, t2v_name)],
            TXT_TO_VCF_VCFNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, t2v_final)],
            VCF_TO_TXT_FILE: [MessageHandler(filters.Document.ALL, v2t_file)],
            VCF_TO_TXT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, v2t_final)],
            MSG_TO_TXT_PROC: [MessageHandler(filters.TEXT & ~filters.COMMAND, m2t_proc)],
            RENAME_C_FILE: [MessageHandler(filters.Document.ALL, rc_file)],
            RENAME_C_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, rc_final)],
            RENAME_F_PROC: [MessageHandler(filters.Document.ALL | filters.TEXT, rf_proc)],
            SPLIT_PROC_FILE: [MessageHandler(filters.Document.ALL, split_file)],
            SPLIT_PROC_NUM: [MessageHandler(filters.TEXT & ~filters.COMMAND, split_final)],
            ADMIN_NAVY_PROC: [MessageHandler(filters.TEXT & ~filters.COMMAND, navy_proc)]
        },
        fallbacks=[CommandHandler('reset', reset)]
    )

    app_tg.add_handler(CommandHandler("start", start))
    app_tg.add_handler(CommandHandler("reset", reset))
    app_tg.add_handler(conv)
    
    print("Bot is alive and polling...")
    app_tg.run_polling()

if __name__ == "__main__":
    main()
