"""
discord_romania_bot.py

Bot Discord con comandi slash in rumeno per gestire i timer delle banche.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional

import discord
from discord.ext import commands
from discord import app_commands


def create_timer_payload(bank_key: str) -> Dict[str, any]:
    """Config per ogni banca (durata, warning e messaggi)."""
    config = {
        "alta": {
            "duration": 7500,
            "warning": 500,
            "warning_msg": "**ALTA** Ie disponibila in 500 de secounde",
            "final_msg": "Banka Alta ie diponibila pentru jaf !",
        },
        "desert": {
            "duration": 7500,
            "warning": 500,
            "warning_msg": "**DESERT** Ie disponibila in 500 de secounde",
            "final_msg": "Banka Desert ie diponibila pentru jaf !",
        },
        "vinewood": {
            "duration": 7500,
            "warning": 500,
            "warning_msg": "**VINEWOOD** Ie disponibila in 500 de secounde",
            "final_msg": "Banka Vinewood ie diponibila pentru jaf !",
        },
        "highway": {
            "duration": 7500,
            "warning": 500,
            "warning_msg": "**HIGHWAY** Ie disponibila in 500 de secounde",
            "final_msg": "Banka Highway ie diponibila pentru jaf !",
        },
        "blaine": {
            "duration": 7500,
            "warning": 500,
            "warning_msg": "**BLAINE** Ie disponibila in 500 de secounde",
            "final_msg": "Banka Blaine ie diponibila pentru jaf !",
        },
        "biju": {
            "duration": 7500,
            "warning": 500,
            "warning_msg": "**BIJU** Ie disponibila in 500 de secounde",
            "final_msg": "Banka Biju ie diponibila pentru jaf !",
        },
        "pacific": {
            "duration": 14400,
            "warning": 1000,
            "warning_msg": "**PACIFIC** Ie disponibila in 1000 de secounde",
            "final_msg": "Banka Pacific ie diponibila pentru jaf !",
        },
    }
    return config[bank_key]


class BankTimerBot(commands.Bot):
    """Discord bot che implementa i timer per le banche con slash command."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

        # Timer attivi e orari di fine
        self.timers: Dict[str, Optional[asyncio.Task]] = {
            "alta": None,
            "desert": None,
            "vinewood": None,
            "highway": None,
            "blaine": None,
            "biju": None,
            "pacific": None,
        }
        self.end_times: Dict[str, Optional[datetime]] = {k: None for k in self.timers}

    async def start_bank_timer(
        self,
        bank_key: str,
        channel: discord.abc.Messageable,
        duration_override: Optional[int] = None,
        warning_override: Optional[int] = None,
    ) -> None:
        """
        Avvia il timer per una banca.

        duration_override: se specificato, usa questa durata invece di quella di default.
        warning_override: se specificato, usa questo offset per il warning.
        """
        cfg = create_timer_payload(bank_key)
        duration = duration_override if duration_override is not None else cfg["duration"]
        warning = warning_override if warning_override is not None else cfg["warning"]
        warning_msg = cfg["warning_msg"]
        final_msg = cfg["final_msg"]

        # Se c'è un timer già attivo per quella banca, lo cancello
        existing: Optional[asyncio.Task] = self.timers.get(bank_key)
        if existing is not None:
            existing.cancel()

        # Salvo l'orario di fine
        self.end_times[bank_key] = datetime.utcnow() + timedelta(seconds=duration)

        async def timer_coroutine():
            try:
                # Warning se ha senso, altrimenti aspetta direttamente tutta la durata
                if warning > 0 and warning < duration:
                    await asyncio.sleep(duration - warning)
                    await channel.send(warning_msg)
                    await asyncio.sleep(warning)
                else:
                    await asyncio.sleep(duration)

                await channel.send(final_msg)
            except asyncio.CancelledError:
                pass
            finally:
                self.end_times[bank_key] = None
                self.timers[bank_key] = None

        task = asyncio.create_task(timer_coroutine())
        self.timers[bank_key] = task

    async def report_remaining(self, bank_key: str) -> int:
        """Ritorna i secondi rimasti per una banca (0 se nessun timer)."""
        end_time = self.end_times.get(bank_key)
        if end_time is None:
            return 0
        remaining = int((end_time - datetime.utcnow()).total_seconds())
        return max(remaining, 0)

    async def reset_timer(self, bank_key: str) -> None:
        """Annulla il timer per una banca e resetta lo stato."""
        existing = self.timers.get(bank_key)
        if existing is not None:
            existing.cancel()
            self.timers[bank_key] = None
        self.end_times[bank_key] = None

    async def setup_hook(self) -> None:
        """Sync dei comandi quando il bot è pronto."""
        await self.tree.sync()

    # ------- HELPER USATO DAI COMANDI /add -------

    async def handle_add(
        self,
        interaction: discord.Interaction,
        bank_key: str,
        seconds: int,
    ) -> None:
        """Gestisce la logica comune per /add..."""
        if seconds <= 0:
            await interaction.response.send_message(
                "Numarul de secunde trebuie sa fie mai mare ca 0.",
                ephemeral=True,
            )
            return

        # Risposta privata
        await interaction.response.send_message(
            f"Cronometru manual pornit pentru Banka {bank_key.capitalize()} ({seconds} secunde)!",
            ephemeral=True,
        )

        # Messaggio pubblico + timer
        if interaction.channel is not None:
            await interaction.channel.send(
                f"BANCA {bank_key.upper()} VA FI DISPONIBILA DUPA {seconds} DE SECUNDE"
            )
            # Warning fisso a 500 secunde, se possibile
            warning_override = 500 if seconds > 500 else 0
            await self.start_bank_timer(
                bank_key,
                interaction.channel,
                duration_override=seconds,
                warning_override=warning_override,
            )


bot = BankTimerBot()

# --------------------------------------------------------------------
#                   COMANDI SLASH PER OGNI BANCA
# --------------------------------------------------------------------


# ---------- /bank... (usa durata di default) ----------

def make_bank_command(name: str):
    @bot.tree.command(
        name=f"bank{name}",
        description=f"Porneste cronometrul pentru Banka {name.capitalize()}",
    )
    async def _cmd(interaction: discord.Interaction) -> None:  # type: ignore
        # Se c'è già un timer attivo, non lo resettiamo
        if (
            bot.timers.get(name) is not None
            and bot.end_times.get(name) is not None
        ):
            await interaction.response.send_message(
                "Acest comand a fost folosit deja",
                ephemeral=True,
            )
            return

        cfg = create_timer_payload(name)
        duration = cfg["duration"]

        await interaction.response.send_message(
            f"Cronometru pornit pentru Banka {name.capitalize()}!",
            ephemeral=True,
        )

        if interaction.channel is not None:
            await interaction.channel.send(
                f"BANCA {name.upper()} VA FI DISPONIBILA DUPA {duration} DE SECUNDE"
            )
            await bot.start_bank_timer(name, interaction.channel)


for _bank in ["alta", "desert", "vinewood", "highway", "blaine", "biju", "pacific"]:
    make_bank_command(_bank)


# ---------- /alta, /desert, ecc. (tempo rimanente) ----------

def make_remaining_command(name: str):
    @bot.tree.command(
        name=name,
        description=f"Afiseaza timpul ramas pentru Banka {name.capitalize()}",
    )
    async def _cmd(interaction: discord.Interaction) -> None:  # type: ignore
        seconds_left = await bot.report_remaining(name)
        await interaction.response.send_message(
            f"Banka {name.capitalize()} are {seconds_left} Secunde"
        )


for _bank in ["alta", "desert", "vinewood", "highway", "blaine", "biju", "pacific"]:
    make_remaining_command(_bank)


# ---------- /resetalta, /resetdesert, ecc. ----------

def make_reset_command(name: str):
    @bot.tree.command(
        name=f"reset{name}",
        description=f"Reseteaza cronometrul pentru Banka {name.capitalize()}",
    )
    async def _cmd(interaction: discord.Interaction) -> None:  # type: ignore
        await bot.reset_timer(name)
        await interaction.response.send_message(
            f"Timerul pentru Banka {name.capitalize()} a fost resetat!",
            ephemeral=True,
        )


for _bank in ["alta", "desert", "vinewood", "highway", "blaine", "biju", "pacific"]:
    make_reset_command(_bank)


# ---------- /addalta, /adddesert, ecc. ----------

def make_add_command(name: str):
    @bot.tree.command(
        name=f"add{name}",
        description=(
            f"Porneste un cronometru manual pentru Banka {name.capitalize()} "
            f"cu numarul de secunde specificat"
        ),
    )
    @app_commands.describe(secunde="Numarul de secunde")
    async def _cmd(
        interaction: discord.Interaction,
        secunde: int,
    ) -> None:  # type: ignore
        await bot.handle_add(interaction, name, secunde)


for _bank in ["alta", "desert", "vinewood", "highway", "blaine", "biju", "pacific"]:
    make_add_command(_bank)


# --------------------------------------------------------------------
#                            EVENTI
# --------------------------------------------------------------------


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


if __name__ == "__main__":
    # METTI QUI IL TUO TOKEN
    bot.run("BOT_TOKEN")
