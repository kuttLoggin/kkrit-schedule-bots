locale-name = 🇷🇺 Русский

welcome =
    👋 Привет, { $user_name }!
    💡 Я буду каждый день отправлять расписание лент твоей группы
    🧐 Работаю в ЛС и беседе

    🪄 Напиши /settings чтобы меня настроить

welcome-group =
    👋 Здравствуйте!
    💡 Я буду каждый день отправлять расписание лент вашей группы

    🪄 <b>Администратор чата</b> должен настроить меня /settings

welcome-btn-invite_in_chat = 💭 Пригласить в беседу

change-lang-btn = ✏ Изменить язык
change-lang-menu = ✏ Выбрано: { locale-name }
change-lang-success = ✔ Язык изменён на { locale-name }

err-not_admin = ❌ Вы не администратор, вам не доступно это действие
err-unknown = ❌ Неизвестная ошибка, сообщите об этом разработчику

command-schedule = Показать расписание
command-settings = Настроить бота
command-report = Отправить репорт

settings-new-hull = 🧐 Сначала выберите свой <b>корпус</b>
settings-new-group = 🤔 Выберите свою <b>группу</b>
settings-success = ✅ Готово! Каждый день я буду отправлять сюда расписание

settings-active_btn =
    {
        $active ->
        [0] 🔕 Слежка выключена
        *[other] 🔔 Слежка включена
    }
settings-pin_msg_btn =
    {
        $active ->
        [0] ❌ Закрепление расписания
        *[other] ✅ Закрепление расписания
    }
settings-change-pin_msg-err =
    ❗ Мне нужны права администратора в этом чате чтобы закреплять сообщения!
settings-change_btn = ✏ Изменить данные
settings-info =
    {
        $active ->
        [0] 😕 Я <b>не слежу</b> за расписанием!
        *[other] 🥸 Я <b>слежу</b> за расписанием!
    }
   🕋 <b>Ваш корпус</b>: { $hull }
   👥 <b>Ваша группа</b>: { $group }

schedule =
    {
        $edit ->
        [0] ✏ Расписание на <b>{ $date }</b>:
        *[other] ✏ Изменение в расписании на <b>{ $date }</b>:
    }
    {
        $tapes ->
        [None] ❌ У вас нет лент
        *[other] { $tapes }
    }
    👀 Что-то не так? <a href="t.me/{ $bot_username }?start=report">Сообщите нам</a>

report-start =
    🧐 Заметили ошибку? Или у вас есть предложение?
    ✏ Напишите <a href="{ $admin_link }">администратору</a>
report-admin-info =
    📍 <b>Репорт</b> от { $user_name } [<code>{ $user_tg_id }</code>]
report-sented =
    ✅ Ваше сообщение отправлено администратору!

report-err_sent =
    ❌ Ваше сообщение не удалось отправить администратору
    ⏳ Пожалуйста, попробуйте позже
report-cancel_send_report = ❌ Отмена
