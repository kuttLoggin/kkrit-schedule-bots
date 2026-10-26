locale-name = 🇷🇺 Русский

welcome =
    👋 Здравствуйте, { $user_name }!
    💡 Я буду каждый день отправлять расписание ваших лент

    🪄 Напиши /settings чтобы меня настроить

welcome-group =
    👋 Здравствуйте!
    💡 Я буду каждый день отправлять расписание ваших лент

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

settings-new-hull = 🧐 Сначала выберите выберите свой <b>корсуп</b>
settings-new-group =
    🤔 Выберите свою <b>группу(ы)</b> которую вы <b>Курируете</b>, после этого нажмите на кнопку: <b>Готово</b>
    ❗ Если вы не куратор, то нажмите на кнопку: <b>У меня нет своей группы</b>
settings-new-group-not_group = ❌ У меня нет своей группы
settings-new-group-done_kb = ✅ Готово
settings-new-name =
    ✏ Напишите вашу <b>фамилию и инициалы</b> (точно как в расписании)
    👀 Пример: Алексей В.Н.
settings-new-name_err =
    ❌ Вы написали вашу <b>фамилию и инициалы</b> не по формату
    ❗ Пожалуйста, напишите следуя примеру: Алексей В.Н.

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
settings-change-pin_msg-err = ❗ Мне нужны права администратора в этом чате чтобы закреплять сообщения!
settings-change_btn = ✏ Изменить данные
settings-info =
    {
        $active ->
        [0] 😕 Я <b>не слежу</b> за расписанием!
        *[other] 🥸 Я <b>слежу</b> за расписанием!
    }
    🕋 <b>Ваш корпус</b>: { $hull }
    👥 <b>Ваши группы</b>: { $group }
    💼 <b>ФИО</b>: { $name }

schedule =
    {
        $edit ->
        [0] 📝 Ваше расписание на <b>{ $date }</b>:
        *[other] 📝 Изменение в вашем расписании на <b>{ $date }</b>:
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
