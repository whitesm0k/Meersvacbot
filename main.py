import discord
from discord import app_commands
from discord.ui import Button, View
from discord.ext import commands
import logging
import json
import os
from datetime import datetime

# --- НАСТРОЙКИ ---
TICKET_CATEGORY_NAME = "✦ 𝗩𝗮𝗰𝗮𝗻𝗰𝗶𝗲𝘀 ✦"
ADMIN_ROLE_ID = 1547658831490719744
HR_ROLE_ID = 1554813015139024927

# --- ПОЛУЧЕНИЕ ТОКЕНА ---
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    try:
        with open("token.txt", "r", encoding="utf-8") as f:
            TOKEN = f.read().strip()
    except FileNotFoundError:
        print("❌ Ошибка: файл token.txt не найден!")
        exit()

if not TOKEN:
    raise RuntimeError("❌ Токен не найден. Проверь token.txt и запусти снова.")

DATA_FILE = "vacancy_stats.json"
STATUS_FILE = "vacancy_status.json"

# --- ЛОГИРОВАНИЕ ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# --- ИНИЦИАЛИЗАЦИЯ БОТА ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

claimed_tickets = {}
stats_data = {}
vacancy_status = {}


# --- ЗАГРУЗКА ДАННЫХ ---
def load_stats():
    global stats_data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                stats_data = json.load(f)
        except:
            stats_data = {"total_closed": 0, "users": {}, "last_update": None}
    else:
        stats_data = {"total_closed": 0, "users": {}, "last_update": None}


def save_stats():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(stats_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Ошибка сохранения статистики: {e}")


def load_status():
    global vacancy_status
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                vacancy_status = json.load(f)
            vacancy_status = {"Media": vacancy_status.get("Media", False),
                              "Support": vacancy_status.get("Support", False)}
        except:
            vacancy_status = {"Media": False, "Support": False}
    else:
        vacancy_status = {"Media": False, "Support": False}


def save_status():
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(vacancy_status, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Ошибка сохранения статусов: {e}")


load_stats()
load_status()


# ==========================================
# КНОПКИ И ВИДЫ
# ==========================================

class VacancyTypeButton(Button):
    def __init__(self, vac_name):
        super().__init__(label=vac_name, style=discord.ButtonStyle.blurple, custom_id=f"vac_{vac_name.lower()}")

    async def callback(self, interaction: discord.Interaction):
        msg_id = interaction.message.id
        if not hasattr(bot, 'temp_ticket_data'):
            bot.temp_ticket_data = {}
        if msg_id not in bot.temp_ticket_data:
            bot.temp_ticket_data[msg_id] = {}

        bot.temp_ticket_data[msg_id]['vacancy_type'] = self.label

        # При выборе вакансии сразу создаем тикет, вопросы будут в канале
        await interaction.response.send_message("⏳ Создаю канал для вашей заявки...", ephemeral=True)

        data = bot.temp_ticket_data[msg_id]
        await self.create_ticket_channel(interaction, data)

        # Удаляем временные данные
        if msg_id in bot.temp_ticket_data:
            del bot.temp_ticket_data[msg_id]

    async def create_ticket_channel(self, interaction: discord.Interaction, data: dict):
        user = interaction.user
        guild = interaction.guild

        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(name=TICKET_CATEGORY_NAME, reason="Авто-создание категории вакансий")

        ticket_count = sum(
            1 for ch in category.channels if isinstance(ch, discord.TextChannel) and ch.name.startswith("vac-"))
        ticket_number = ticket_count + 1
        channel_name = f"vac-{ticket_number}"

        hr_role = guild.get_role(HR_ROLE_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if hr_role:
            overwrites[hr_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_channel = await category.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            topic=f"Вакансия: {data['vacancy_type']}",
            reason=f"Заявка на вакансию от {user.id}"
        )

        role = guild.get_role(ADMIN_ROLE_ID)
        mention = role.mention if role else "@everyone"

        # Формируем приветственное сообщение с вопросами
        vacancy_type = data['vacancy_type']

        if vacancy_type == "Media":
            questions_text = (
                "🎬 **Вакансия: Media**\n\n"
                "👋 Привет, {user}! Спасибо, что хочешь присоединиться к команде.\n\n"
                "📝 **Пожалуйста, ответь на следующие вопросы в этом канале:**\n"
                "1. Сколько вам лет?\n"
                "2. Умеете ли монтировать?\n"
                "3. Сколько вы находитесь на проекте?\n"
                "4. Есть ли у вас наш ключ?\n\n"
                "💡 Можешь отвечать списком или просто текстом — главное, чтобы были ответы на все пункты."
            ).format(user=user.mention)
        else:  # Support
            questions_text = (
                "🛠️ **Вакансия: Support**\n\n"
                "👋 Привет, {user}! Спасибо, что хочешь помогать игрокам.\n\n"
                "📝 **Пожалуйста, ответь на следующие вопросы в этом канале:**\n"
                "1. Сколько вам лет?\n"
                "2. Умеете ли помогать игрокам в тикетах?\n"
                "3. Сколько вы находитесь на проекте?\n"
                "4. Есть ли у вас наш ключ?\n"
                "5. Знаете ли вы основу и решение проблем с читом?\n\n"
                "💡 Можешь отвечать списком или просто текстом — главное, чтобы были ответы на все пункты."
            ).format(user=user.mention)

        await ticket_channel.send(f"{mention} 🚨 **Новая заявка на вакансию!**")

        welcome_embed = discord.Embed(
            title="Ваша заявка создана!",
            description=questions_text,
            color=discord.Color.blurple()
        )
        welcome_embed.add_field(name="Автор", value=user.mention, inline=True)
        welcome_embed.add_field(name="Вакансия", value=vacancy_type, inline=True)
        welcome_embed.add_field(name="Статус", value="⏳ Ожидает заполнения", inline=False)
        welcome_embed.set_footer(text=f"ID заявки: #{ticket_number}")

        control_view = View(timeout=None)
        control_view.add_item(ClaimTicketButton())
        control_view.add_item(CloseTicketButton())

        await ticket_channel.send(embed=welcome_embed, view=control_view)

        await interaction.followup.send(
            embed=discord.Embed(title="Готово", description=f"Канал создан: <#{ticket_channel.id}>",
                                color=discord.Color.green()),
            ephemeral=True
        )


class ClaimTicketButton(Button):
    def __init__(self):
        super().__init__(label="Взять в работу", style=discord.ButtonStyle.green, custom_id="claim_ticket")

    async def callback(self, interaction: discord.Interaction):
        channel_id = interaction.channel.id
        user = interaction.user
        can_claim = False

        if HR_ROLE_ID and any(role.id == HR_ROLE_ID for role in user.roles):
            can_claim = True
        if any(role.permissions.administrator for role in user.roles):
            can_claim = True

        if not can_claim:
            await interaction.response.send_message("❌ Только HR и админы могут брать заявки.", ephemeral=True)
            return

        if channel_id in claimed_tickets:
            claimer_id = claimed_tickets[channel_id]
            claimer = interaction.guild.get_member(claimer_id)
            name = claimer.display_name if claimer else "Пользователь"
            if claimer_id != user.id:
                await interaction.response.send_message(f"❌ Эта заявка уже взята: {name}.", ephemeral=True)
                return
            else:
                await interaction.response.send_message("ℹ️ Заявка уже у вас в работе.", ephemeral=True)
                return

        claimed_tickets[channel_id] = user.id
        embed = discord.Embed(title="Заявка взята в работу", description=f"{interaction.user.mention} взял эту заявку.",
                              color=discord.Color.green())
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✅ Вы взяли заявку в работу.", ephemeral=True)


class CloseTicketButton(Button):
    def __init__(self):
        super().__init__(label="Закрыть заявку", style=discord.ButtonStyle.red, custom_id="close_ticket")

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Закрывать заявки могут только администраторы.", ephemeral=True)
            return

        global stats_data
        stats_data["total_closed"] += 1
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        user_id = str(interaction.user.id)

        if user_id not in stats_data["users"]:
            stats_data["users"][user_id] = {"total": 0, "today": 0, "week": 0, "last_close_date": ""}

        user_stats = stats_data["users"][user_id]
        if user_stats["last_close_date"] != date_str:
            user_stats["today"] = 0
        user_stats["today"] += 1
        user_stats["last_close_date"] = date_str
        user_stats["week"] += 1
        user_stats["total"] += 1
        stats_data["last_update"] = date_str
        save_stats()

        try:
            await interaction.channel.delete(reason=f"Закрытие администратором {user_id}")
            if interaction.channel.id in claimed_tickets:
                del claimed_tickets[interaction.channel.id]
        except Exception as e:
            await interaction.response.send_message("Ошибка удаления канала.", ephemeral=True)


class StartVacancyButton(Button):
    def __init__(self):
        super().__init__(label="💼 Подать заявку на вакансию", style=discord.ButtonStyle.blurple,
                         custom_id="start_vacancy")

    async def callback(self, interaction: discord.Interaction):
        msg_id = interaction.message.id
        if not hasattr(bot, 'temp_ticket_data'):
            bot.temp_ticket_data = {}
        bot.temp_ticket_data[msg_id] = {}

        view = View(timeout=120)

        if vacancy_status.get("Media", False):
            view.add_item(VacancyTypeButton("Media"))
        else:
            view.add_item(Button(label="Media (Набор закрыт)", style=discord.ButtonStyle.grey, disabled=True))

        if vacancy_status.get("Support", False):
            view.add_item(VacancyTypeButton("Support"))
        else:
            view.add_item(Button(label="Support (Набор закрыт)", style=discord.ButtonStyle.grey, disabled=True))

        await interaction.response.send_message(
            "👋 Привет! Выберите **вакансию**, на которую хотите подать заявку:",
            view=view,
            ephemeral=True
        )


class VacancyPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)


# ==========================================
# SLASH-КОМАНДЫ
# ==========================================

@bot.tree.command(name="openvacmed", description="Открыть набор на вакансию Media")
@app_commands.checks.has_permissions(administrator=True)
async def open_vac_med(interaction: discord.Interaction):
    vacancy_status["Media"] = True
    save_status()
    await interaction.response.send_message("✅ Набор на вакансию **Media** открыт.", ephemeral=True)


@bot.tree.command(name="openvacsupp", description="Открыть набор на вакансию Support")
@app_commands.checks.has_permissions(administrator=True)
async def open_vac_supp(interaction: discord.Interaction):
    vacancy_status["Support"] = True
    save_status()
    await interaction.response.send_message("✅ Набор на вакансию **Support** открыт.", ephemeral=True)


@bot.tree.command(name="closevacmed", description="Закрыть набор на вакансию Media")
@app_commands.checks.has_permissions(administrator=True)
async def close_vac_med(interaction: discord.Interaction):
    vacancy_status["Media"] = False
    save_status()
    await interaction.response.send_message("❌ Набор на вакансию **Media** закрыт.", ephemeral=True)


@bot.tree.command(name="closevacsupp", description="Закрыть набор на вакансию Support")
@app_commands.checks.has_permissions(administrator=True)
async def close_vac_supp(interaction: discord.Interaction):
    vacancy_status["Support"] = False
    save_status()
    await interaction.response.send_message("❌ Набор на вакансию **Support** закрыт.", ephemeral=True)


@bot.tree.command(name="setupvacancy", description="Разместить панель подачи заявок на вакансии")
@app_commands.checks.has_permissions(administrator=True)
async def setup_vacancy(interaction: discord.Interaction):
    view = VacancyPanelView()
    view.add_item(StartVacancyButton())

    embed = discord.Embed(
        title="💼 Набор на вакансии MeersProject",
        description=(
            "👋 Привет! Здесь ты можешь подать заявку на вакансию в нашей команде.\n\n"
            "📋 **Правила подачи заявки:**\n"
            "1. Нажмите на кнопку ниже и выберите интересующую вакансию.\n"
            "2. Бот создаст канал, где будут указаны вопросы для вашей вакансии.\n"
            "3. Ответьте на вопросы в канале.\n\n"
            "⏳ Статус набора отображается на кнопках."
        ),
        color=discord.Color.blurple()
    )
    embed.set_footer(text="MeersProject Support System")

    try:
        file = discord.File("logo.png", filename="logo.png")
        embed.set_thumbnail(url="attachment://logo.png")
        await interaction.response.send_message(embed=embed, view=view, file=file)
    except FileNotFoundError:
        logger.warning("⚠️ Файл logo.png не найден! Панель отправлена без логотипа.")
        await interaction.response.send_message(embed=embed, view=view)


# ==========================================
# СОБЫТИЯ БОТА И ЗАПУСК
# ==========================================

@bot.event
async def on_ready():
    logger.info(f"✅ Бот запущен! Имя: {bot.user.name} (ID: {bot.user.id})")

    try:
        synced = await bot.tree.sync()

        logger.info(f"📡 Синхронизировано команд: {len(synced)}")
        print("-" * 40)
        print(f"Бот онлайн: {bot.user.name}")
        print(f"Подключён к серверам: {len(bot.guilds)}")
        print(f"Синхронизировано команд: {len(synced)}")

        if len(synced) == 0:
            print("⚠️ ВНИМАНИЕ: Синхронизировано 0 команд!")
            print("   1. Проверь права бота: 'Использование команд приложений'.")
            print("   2. Убедись, что ты запускаешь этот файл, а не старый.")
        else:
            print("✅ Команды успешно загружены:")
            for cmd in synced:
                print(f"   - /{cmd.name}")
        print("-" * 40)

    except discord.Forbidden:
        logger.error("❌ Ошибка 403: У бота нет прав для синхронизации команд.")
        print("⚠️ Проверь права бота на сервере! Нужно право 'Использование команд приложений'.")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка синхронизации: {e}")
        print(f"⚠️ Произошла ошибка: {e}")


if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.critical(f"💥 Критическая ошибка при запуске бота: {e}")
