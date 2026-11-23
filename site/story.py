"""Shared read-aloud pages for the printed campaign. The server keeps unopened pages."""
import engine as E
import promises
import roadside


# Location, testimony and physical clue. Only the witness at the current stop speaks.
WITNESSES = {
    2: ("Йотт греет над свечой металлическую бирку. Вдова молча кладёт рядом суповую ложку: последние четыре насечки совпадают. «Уберите мой подлог — и завтра ей перестанут отпускать муку».", "оттиск бирки Йотта"),
    3: ("Энна зовёт сына к ужину, постучав ложкой по ольхе. Из дома выходит мальчик с теми же зарубками на ободке миски. Она спрашивает у него дорогу к собственному порогу.", "ободок ольховой миски"),
    4: ("Таш вынимает пробку из пустой бочки. Внутри кто-то чихает. Это не пассажир: на внутренней стороне обода записано имя женщины, простудившейся сегодня утром.", "бумажная лента из обода"),
    5: ("Мирт сушит над очагом конверт. В нём деньги на починку лодки и просьба не рассказывать отцу. Она узнаёт свой подростковый почерк. Отец умер до первой зимы, когда вскрылся лёд.", "конверт с рыбьей чешуйкой"),
    7: ("Оса даёт приложить ухо к меловой стене. За камнем раздаётся слово «обед», потом звякает ложка. Завтрашняя смена ещё жива; по ведомости плату за неё уже внесли.", "меловой слепок ведомости"),
    8: ("Эля прикладывает два завещания к окну. Даты разные, но на обоих листах одно чернильное пятно в форме запятой. Мельничиха прикрывает рукой имя дочери, прежде чем разрешить вам снять оттиск.", "двойной оттиск печати"),
    9: ("Эр ставит камертон ножкой на скамью. Слабый толчок отзывается в локтях всех сидящих. «Теперь по одному встаньте». Когда скамья пуста, остаётся ещё один удар.", "ритм пустого места"),
    10: ("Иль снимает с подсвечника холодную монету. На её ребре выбита дата завтрашних похорон. Монету жертвовал король Аст; Иль помнит, как на прошлой неделе подавала ему горячее молоко.", "оттиск ребра монеты"),
}

# Voices heard at the council. The same witness answers differently after each personal choice.
PERSONAL = {
    "H01": ("Швея выворачивает рукав. Стежок Сойки идёт дальше, через манжету: брат дошёл до следующей деревни.", "Швея замечает потёртую подкладку Сойки и молча передаёт запасную иглу. Она согласна подождать, пока Сойка сама развернёт карту."),
    "H02": ("Садовница приносит Лиору яблоко с привитой ветки. Оно пахнет дымом дома, у которого раньше кончалась дорога.", "В приёмной мальчик просит Лиора нарисовать дорогу по памяти. На повороте он сам дорисовывает старую яблоню."),
    "H03": ("Лодочник узнаёт след чешуйчатого сапога Ильвы на обороте лоцманской карты. Так на другом берегу отмечают брод.", "Сапожница у дверей прикладывает колодку к кожаному сапогу Ильвы. Такую пару когда-то заказали для пути в обратную сторону."),
    "H04": ("Йотт прислал Брому детскую дощечку со счётом смен. Подпись на акте обвала скопировали с неё спустя двенадцать лет.", "В переплёте судебной книги Бром находит карандашную дату под подписью. У него остаётся выбор, вынести ли черновик на свет."),
    "H05": ("Глухая ученица Торы выкладывает на стол ненужные теперь жетоны налога на слух. Ими прижимают углы списка свидетелей.", "Сборщик возвращает Торе расписку за слух. На обороте — имена тех, за кого отложили платёж. Он просит оставить бумагу у неё."),
    "H06": ("От Келловой каски пахнет свежим мелом: напарница сама принесла её из выработки. Она узнала его по кривой метке на козырьке.", "Келл слышит знакомый свист. В толпе женщина стучит по его второй каске костяшкой пальца, как перед каждой общей сменой."),
    "H07": ("Воск из письма Мары растёкся на две печати. Прачка узнала почерк сестры и принесла свой ответ — один лист без просьбы вернуть мёртвую.", "У дверей раздают пустые конверты. Мара получает один с обратным адресом сестры. Печать последнего письма принадлежит только ей."),
    "H08": ("В зале Яса узнаёт лицо из горького сна. Назвав этому человеку его детское прозвище, она слышит в ответ своё.", "Покупатель сладкого сна возвращает Ясе пузырёк. Внутри завёрнут рисунок лица, которого он боялся не вспомнить утром."),
    "H09": ("Братство принесло к слушанию одну закопчённую свечу Весты. Люди по очереди закрывают огонёк рукой, пока говорит сосед.", "Веста находит в кармане целую свечу. Женщина, которой досталась последняя ложка, просит дать огонь после слушания, по дороге домой."),
    "H10": ("Дезертир узнаёт второй герб Ивара и встаёт рядом добровольно. Он держит щит так, чтобы его видели с обеих сторон.", "Старый оруженосец Ивара чинит застёжку, отвернувшись к окну. В книге явившихся он оставляет место для подписи без герба."),
    "H11": ("Королева отдаёт Рене приглашение. На нём две одинаковые кляксы: обе дуэлянтки учились писать за одной партой.", "Соперница Рены складывает шпагу в ножны и предлагает встретиться на рассвете за хлебом. Приглашение можно открыть вдвоём."),
    "H12": ("Под поднятым знаменем Оллена младший писарь вслух перечисляет тех, кого принято считать перебежчиками. Караул отвечает «здесь».", "Гир ставит у свёрнутого знамени Оллена кружку. К ней выстраиваются по одному; каждому Оллен может назвать товарища без свидетелей."),
    "H13": ("В расщелине печати Ней видит крупицу чёрной соли. Так учитель отмечал обратную дорогу из скалы. След ведёт домой.", "Ученица солемера протягивает Нею сухую рукавицу учителя. Соль тянется к левой ладони так же, как раньше к западу."),
    "H14": ("Тея перерисовывает узор для каменщицы. Та называет залы по звуку шагов своей матери — ещё до того, как увидит рисунок.", "В закрытом зеркале Теи тихо скребётся мелок. С обратной стороны кто-то ведёт тот же урок черчения."),
    "H15": ("Часовщик возвращает Эссу пропущенную секунду: перед присягой весь зал молчит ровно столько, чтобы самый тихий успел ответить.", "Часовщик кладёт перед Эссом маятник. Тот качается в такт его дыханию до тех пор, пока очередь не доходит до него."),
    "H16": ("Ключ Грана подошёл к маленькой калитке для детей. Сторож приносит его обратно на ленте из детского рукава.", "Сторож узнаёт ключ у Грана на поясе. Теперь, прежде чем открыть ворота, он спрашивает, кого первым ждут снаружи."),
    "H17": ("Урса держит паузу. Из самого дальнего ряда отзывается женщина, которую годами отмечали на перекличках как отсутствующую.", "Урса допевает последний голос и слышит за дверью продолжение. У караульной песни появился новый куплет — его сочинили ожидавшие снаружи."),
    "H18": ("Плотник отдаёт Роху щепку с материнского мостка. Зарубки оказались мерками роста: кто-то здесь помнит, как Рох был маленьким.", "Сопровождавшая беженцев плотница говорит Роху, какая доска выдержит телегу. Голос у неё его материнский, но дорогу она выбирает сама."),
}


# The keys here are server-side page IDs; a button submission includes its page's current ID.
PAGES = {
    "prologue": ("Нулевой удар", "У брода сушат девять ложек. Восьмилетняя девочка убирает одну за пазуху. «Когда мама забудет меня, она всё равно сварит на двоих. Слышите? Ложки стукаются о край». На звоннице мокрая верёвка натягивается сама. Лада не выпускает её из рук.",
                 "До первого удара есть время оставить один знак. Что вы предложите девочке?",
                 [("ribbon", "Завязать ленту на запястье матери"), ("spoon", "Отдать лишнюю ложку лодочнику")]),
    "bell": ("Колокол у брода", "С нижней ступени отмели выходят гончие. На мокрых ошейниках вместо кличек стоят номера. Лада кричит, что не сможет одновременно удержать верёвку и назвать всех пропавших. Первым лодочник забывает слово «дом».",
             "Разыграйте три раунда и отметьте исход. Коромысло требует двух успехов в зоне 3 против 7. Для песни нужны Воля 8 в зоне 3 и свой флакон. Язык можно снять в зоне 4 после победы над стражей.",
             [("hold", "Удержали коромысло"), ("song", "Спели с Ладой и отдали флакон"), ("tongue", "Сняли медный язык"), ("empty", "На третьем ударе мост опустел")]),
    "records": ("Соль в ведомости", "", "", []),
    "copies": ("Кому доверить копии", "На обоих листах графу «плата внесена» заполнили до рождения младшего свидетеля. Старуха из Братства Пустых Ложек просит разрешения огласить список. Девочка рядом с ней накрывает своё имя пальцем. Курьер двора предлагает запечатанный тубус. «У вас хоть есть ключ от вашего тубуса?» — спрашивает старуха. Курьер ощупывает пояс и садится.",
               "Одна копия поедет к воротам с вами. Где будет храниться вторая?",
               [("court", "Сдать копию в канцелярию · +1 местной славы"), ("families", "Раздать списки семьям · голос улицы"), ("hidden", "Спрятать копию с казной · +3 серебра")]),
    "gateRoad": ("Дорога к Щучьему Броду", "Вперёд поскакал курьер. Остановившись, он одним движением рисует в пыли ворота и толпу за ними. Просит запомнить рисунок: до Красного Яра он может забыть, зачем его послали.",
                 "Доберитесь по карте до Красного Яра. Там Гир ждёт у ворот.", [("arrive", "Встретить Гира у ворот")]),
    "gate": ("Дверь, которую держат снаружи", "Снаружи мокрой тряпкой прикрывают петлю, чтобы ворота не скрипнули и не разбудили младенца. Изнутри барабанщик отсчитывает начало штурма. Гир просовывает под створку край полкового знамени. С той стороны его чинят на ощупь.",
             "Удержите ворота четыре раунда или добейтесь двух успехов переговоров в зоне 2 против 8 + ступень. При прорыве времени хватит только на одно спасение. Отметьте, что случилось за столом.",
             [("hold", "Гарнизон выдержал осаду"), ("parley", "Знамя помогло договориться"), ("lada", "После прорыва спасли Ладу"), ("wagon", "После прорыва спасли обоз")]),
    "courtRoad": ("Раковина для королевы", "Гир поднимает из грязи раковину. Приложив её к уху, каждый слышит голос собственного монарха. Все голоса просят об одном: «Дайте мне ещё одну ночь». Эту вещь придётся показать королеве Эйре лично.",
                  "Вернитесь по карте в Вельн. Две записи из областей дают право войти во дворец.", [("enter", "Войти на слушание")]),
    "hearing": ("Слушание без подсудимого", "Эйра приносит две книги. В первой восемьдесят семь лет назад десять правителей подписали договор: затвор держит берег, пока ему отдают имена погибших. Вторая раскрывается сама — здесь писали вчера. Девятнадцать лет назад казначеи впервые внесли живого. «Я знала, — говорит Эйра. — Я хотела сначала успеть вывезти людей».",
                "Писарь спрашивает, от чьего имени вы выступаете.",
                [("square", "Вынести копию к семьям · один день"), ("serve", "Предложить службу"), ("council", "Созвать тайный совет")]),
    "council": ("Три места за ширмой", "За ширмой три табурета. На первом лежит улика, на втором ждёт приглашённый свидетель, третий придётся вынести к публике. Пока на нём никто не сидит, писарь рисует на полу черту, за которую запрещено выносить бумаги.",
                "Разыграйте три шага заговора по книге правил. Учтите цену попыток на планшете. Подозрение 4 немедленно ведёт к суду.",
                [("uncovered", "Дело огласили · подозрение 0–2"), ("trial", "Заговор раскрыли · применили решение суда на столе")]),
    "original": ("Оригинал", "Эйра кладёт на стол ключ. На его плоской стороне проступает ваш почерк — такой, каким вы оставляли записки на кухне. Писарь отодвигает чернильницу: теперь, чтобы передать власть, не требуется ещё одной подписи.",
                 "Кому передаёте оригинал договора?",
                 [("crown", "Передать Эйре · королевский голос"), ("street", "Отдать семьям · голос улицы"), ("keep", "Сохранить оригинал · один раз сорвать сигнал Хранителя")]),
    "heartRoad": ("Лестница под звонницей", "Из последней ступени вынули камень. На его месте лёгкая деревянная крышка. Она поднимается от малейшего движения воздуха: по ту сторону кто-то дышит и считает вдохи.",
                  "В Трёх Ивах поднимите крышку и расставьте фигурки в подземелье.", [("descend", "Спуститься к Сердцу")]),
    "heart": ("Девятое имя", "Хранитель сушит у затвора две стопки листов. Убирая верхний, он каждый раз придерживает нижний, будто там спит птица. «Я переворачиваю их уже восемьдесят семь лет. Покажите, куда мне положить руки, если я отпущу».",
              "На алтарях в зонах 3 и 5 лежат два набора. Хранитель стоит в 6 до первого взятого набора или попадания. Победите или принесите оба набора в 6 и добейтесь двух успехов разными характеристиками против 8 + ступень. За провал переговоров 1 прямой урон.",
              [("defeat", "Победили Хранителя в бою"), ("treaty", "Заключили договор у затвора"), ("retreat", "Отступили от Сердца")]),
    "retry": ("Ступенька для возвращения", "Наверху девочка поставила кружку с пресной водой. Рядом в пыли остался второй круг: кто-то уже приходил сюда, отдыхал и возвращался вниз.",
              "Отдохните. Повторный вход стоит 2 серебра, при нехватке — один день.", [("return", "Вернуться к Хранителю")]),
    "verdict": ("Чьи имена останутся", "Колокол произносит имя того, кому вы первому протянули руку. Назовите его вслух. Таш кладёт на алтарь карту Соляной Лиги: красными точками стоят пристани, между которыми он готов возить людей. Внизу мелким почерком выведена цена каждого следующего перехода. На обороте карта ещё чиста.", "Решите вместе, кому теперь принадлежит ключ.",
                [("seal", "Запечатать прежний договор"), ("publish", "Опубликовать реестры"), ("open", "Разомкнуть затвор"), ("rule", "Присвоить ключ")]),
}


def initial(table):
    page = {1: "prologue", 2: "records", 3: "gateRoad", 4: "courtRoad", 5: "heartRoad"}[table["party"]["chapter"]]
    return {"page": page, "decisions": {}, "records": [], "history": []}


def story_id(s, realm):
    # Counts and location change the meaning of "take the testimony".
    return f"records-{len(s['records'])}-{realm}" if s["page"] == "records" else s["page"]


def record_page(s, party, table):
    area = party["realm"]
    prompt = "Привезите две записи из разных областей. Подходят Кремноград, Ольховое Княжество, Соляная Лига, Озёрный Венец, Меловая Марка, Семь Меж, Ночесвод и Ледяной Престол."
    if area not in WITNESSES or any(r["realm"] == area for r in s["records"]):
        return ("Соль в ведомости", "На внутренней стороне колокольной меди выступил воск. В его отпечатке видна графа для выдачи пайка. На побережье ещё делают такие ведомости.", prompt, [])
    npc = E.realms[area-1][6]
    paper = "Писарь протягивает ведомость. Пальцы у него чисты, а ваше имя на странице ещё не высохло." if not s["records"] else "Из очереди за хлебом выходит человек. «Я помню вас, — говорит он. — Хотя город, где мы встречались, исчез»."
    choices = [] if table["scene"] or party["weatherDue"] else [
        ("testimony", "Дело или этаж завершены · получить печать"),
        ("paid", "Дело или этаж завершены · печать уже записана"),
        ("loss", "Потерпели поражение · унесли запись"),
        ("wall", "Списать строку со стены · один день"),
    ]
    return (npc[0].upper() + npc[1:], paper + " " + WITNESSES[area][0], prompt + " Если вы в пути или в бою, сперва закройте погоду и активное поле. При поражении запись сохраняется.", choices)


CALLBACKS = {
    "boats": "Гир узнаёт на пороге суда запах смолы. Лада пришла со спасёнными погонщиками, а Фен, так и не привыкший стоять на суше, придерживается за косяк.",
    "ribbon": "Лада перевязывает найденной лентой узелок с хлебом. Дома всегда оставляли вторую порцию; руки помнят это даже в самый дурной день.",
    "spoon": "Лодочник ударяет запасной ложкой о медный котелок. Через воду ему отвечает девочка. Они успели завести собственную переправную азбуку.",
    "court": "У копии из канцелярии есть входящий номер. Стражник вынужден назвать его вслух и впустить свидетеля.",
    "families": "Каждая семья принесла по одной строке вашей копии. Чтобы уничтожить список, пришлось бы обыскать весь берег.",
    "hidden": "В потайном свёртке нашлась складка с отпечатком ладони. Тот, кто однажды спрячет вашу историю, сможет убедиться, что она настоящая.",
    "hold": "Гир приносит засов. Металл выгнут дугой; люди, выстоявшие у ворот, просят повесить его у входа в суд.",
    "parley": "На пороге встречаются два бывших часовых с разных сторон ворот. По одну сторону знамени они впервые стоят добровольно.",
    "lada": "Лада сама приносит раковину из-под ворот. Теперь противоречия в протоколе можно проверить вопросом к живому свидетелю.",
    "wagon": "Возница привозит свидетелей в том самом спасённом обозе. По дороге они успели договориться, кто заговорит первым.",
}


def echoes(table, s):
    page, choices = s["page"], s["decisions"]
    keys = {"records": ["prologue"], "gate": ["copies"], "hearing": ["gate"], "epilogue": ["prologue", "copies", "gate"]}.get(page, [])
    lines = [CALLBACKS[choices[k]] for k in keys if choices.get(k) in CALLBACKS]
    if page == "hearing":
        lines.append("Писарь находит причину первого звона. Девять дней назад дочь Лады, Руту, внесли под двумя разными печатями. В обеих записях один след: Рута выводит у буквы «р» длинный плавник. Затвор стал перепроверять весь реестр живых. На полях девочка приписала: «Это у меня рыба ныряет».")
    if page in ("hearing", "epilogue"):
        for hid in E.claimed(table):
            side = table["heroes"][hid]["fork"]
            if side in ("a", "b"):
                lines.append(PERSONAL[hid][side == "b"])
    return lines + promises.echoes(s)


def visible(table):
    s = table.get("story") or initial(table)
    party, page = table["party"], s["page"]
    if page == "epilogue":
        title, _, passage = E.endings[s["ending"]]
        text = passage + " " + s["postscript"]
        prompt, choices = "Пусть сосед справа скажет, как в новом мире живёт вещь, которую ваш герой помнил за двоих.", []
    elif page == "records":
        title, text, prompt, choices = record_page(s, party, table)
    else:
        title, text, prompt, choices = PAGES[page]
        if page in ("gateRoad", "courtRoad", "heartRoad", "retry", "prologue"):
            area = 6 if page == "gateRoad" else 1
            if party["realm"] != area or party["weatherDue"] or table["scene"]:
                choices = []
                prompt += " Закройте активное поле и дорожную погоду, затем придите в " + E.realms[area-1][0] + "."
            elif page in ("prologue", "gateRoad", "heartRoad", "retry") and not E.claimed(table):
                choices = []
                prompt += " Сначала выберите героя на личном планшете."
            elif page == "retry" and not party["rested"]:
                choices = [("work", "Отработать ночлег · один день")]
                prompt += " Можно устроить привал за припас или отработать ночлег."
        if page == "council" and party["suspicion"] >= 3:
            choices = [choice for choice in choices if choice[0] == "trial"]
        if page == "bell" and (table["scene"] or {}).get("goal") != "песня":
            singers = [hid for hid in E.claimed(table) if "I19" in table["heroes"][hid]["potions"]]
            song_choices = [("song-" + hid, f"Спели с Ладой · флакон отдаёт {E.HERO_BY[hid]['name']}") for hid in singers]
            choices = choices[:1] + song_choices + choices[2:]
        if page == "heart" and table["scene"] and table["scene"].get("keeperBound"):
            choices = [("altar", "На поле подняли первый набор имён")] + choices
        if page == "heart" and "cancelKeeperSignal" in party["flags"]:
            choices = [("cancel", "Предъявить оригинал · отменить текущий сигнал")] + choices
        if page == "gate" and roadside.heard(s, 4, "pilots"):
            choices = choices + [("boats", "При прорыве вызвать лодки Таша для Лады и обоза")]
        if page == "hearing" and roadside.heard(s, 2, "testify"):
            choices = choices + [("widows", "Вызвать Берту и трёх вдов с бирками")]
        if page == "heart" and roadside.heard(s, 9, "rest") and not s.get("usedSilence"):
            choices = [("silence", "Взять паузу Эра · один раз отменить сигнал")] + choices
    if page not in ("bell", "gate", "heart", "epilogue") and party["fightDue"]:
        choices = []
        prompt += " Сначала разыграйте дорожную стычку на поле или отметьте её исход с бумажного стола."
    reports = roadside.chronicle(s)
    arrival = "Эпилог" if page == "epilogue" else f"Глава {party['chapter']}"
    news = [r["news"] for r in reports if r["arrival"] == arrival]
    return {
        "id": story_id(s, party["realm"]), "chapter": party["chapter"], "title": title, "text": text,
        "prompt": prompt, "choices": [{"id": k, "label": v} for k,v in choices],
        "echoes": echoes(table, s), "history": list(s["history"]), "ending": page == "epilogue",
        "meeting": roadside.current(table, s), "roadJournal": reports, "news": news,
        "promises": promises.view(table, s), "verdictReceipt": s.get("verdictReceipt"),
        "milestones": s.get("milestones", []),
    }


def add_day(table):
    party = table["party"]
    party["day"] += 1
    if party["day"] % 3 == 0:
        E.add_tide(table, 1)


def clue(party, name):
    if name not in party["clues"]:
        party["clues"].append(name)


def seal(table):
    table["party"]["seals"] += 1
    E.bank(table)


def local_glory(party, realm):
    party["glory"][realm-1] = min(4, party["glory"][realm-1] + 1)


def begin_battle(table, seat, page):
    party = table["party"]
    kind = {"prologue": "bell", "gateRoad": "siege", "heartRoad": "dungeon", "retry": "dungeon"}[page]
    result = E.start_scene(table, seat, kind)
    if not result["ok"]:
        return result
    scene = table["scene"]
    tier = E.tier_of(party["level"])
    if kind == "siege":
        wave = E.pick_mob(5, tier, 0, False)
        count = E.MEET["simple"][min(6, E.party_n(table))]
        E.spawn_cards(table, wave, count, 5)
        scene["storySiege"] = True
        scene["note"] = "Гир у ворот. В раунде 3 придёт вторая волна другой семьи. Удержите ворота четыре раунда или добейтесь переговоров."
    if kind == "dungeon":
        ref = f"B{2*tier-1:03}"
        scene["door"] = False
        scene["keeperBound"] = True
        scene["title"] = "Сердце под звонницей"
        scene["note"] = "Алтари в 3 и 5. Хранитель ждёт в 6 до первого попадания или взятого набора. Удерживайте его фигурку там до этого события."
        E.spawn_cards(table, ref, 1, 6, hp_each=E.BOSS_BY[ref]["hp"] * E.party_n(table))
    return result


def siege_wave(table, seat):
    """Call after advancing the round. Repeated refreshes cannot summon extra figures."""
    scene = table["scene"]
    if scene and scene.get("storySiege") and scene["round"] >= 3 and not scene.get("secondWave"):
        tier = E.tier_of(table["party"]["level"])
        E.spawn_cards(table, E.pick_mob(5, tier, 1, False), E.MEET["simple"][min(6, E.party_n(table))], 6)
        scene["secondWave"] = True
        E.log(table, seat, "scene", "На склоне показалась вторая волна. Гир разворачивает знамя к дороге.")


def finish_field(table, seat, victory, kind):
    if table["scene"] and table["scene"]["id"] == kind:
        E.end_scene(table, seat, {"victory": victory})


def verdict_result(s, party, choice):
    decisions = s["decisions"]
    if choice == "seal":
        original = decisions.get("original") == "crown"
        realms = [E.realms[i][0] for i, score in enumerate(party["glory"]) if score == 4]
        reason = "Оригинал у Эйры — " + ("да" if original else "нет") + ". Королевства со славой 4 — " + (", ".join(realms) or "ни одного") + ". Для королевского голоса достаточно любого из этих условий."
        return (0 if original or realms else 1), reason
    if choice == "publish":
        return (2 if party["street"] else 3), f"Голосов улицы при публикации — {party['street']}. Для совета семей нужен хотя бы один."
    if choice == "open":
        count = party["portals"].count("open")
        return (4 if count >= 2 else 5), f"Открытых арок при размыкании — {count}. Для связи берегов нужны хотя бы две. След на карте ещё не открывает арку."
    knighted = bool(s.get("knighted"))
    return (6 if knighted else 7), "Посвящение в рыцари на слушании — " + ("есть." if knighted else "отсутствует.") + " От него зависит, признают ли дворы нового правителя."


def postscript(s, party):
    lines = []
    if party["scars"] >= 3:
        lines.append("На карте осталось белое место размером с деревню. Впишите её последнее имя.")
    if party["debts"]:
        lines.append("На рассвете армейский посыльный потребует ваш знак в счёт невыплаченного долга.")
    if s["decisions"].get("council") == "trial":
        lines.append("Первую летопись пишет обвинитель с вашего суда. Только от вас у него есть полная запись.")
    if s["decisions"].get("heart") == "treaty":
        lines.append("Бывший Хранитель устроился переплётчиком. Он охотно чинит любую книгу, кроме списков умерших.")
    else:
        lines.append("У алтаря лежат пустые перчатки Хранителя. Никто не надевает их, и всё-таки листы каждое утро перевёрнуты.")
    return " ".join(lines)


def chapter_totals(party):
    labels = {"silver": "Серебро", "supplies": "Припасы", "seals": "Печати", "level": "Уровень",
              "tide": "Прилив", "scars": "Шрамы", "suspicion": "Подозрение", "shards": "Осколки",
              "street": "Голос улицы", "debts": "Армейские долги", "day": "День"}
    totals = {label: party[key] for key, label in labels.items()}
    totals.update({"Слава · " + r[0]: score for r, score in zip(E.realms, party["glory"])})
    return totals


def choose(table, seat, action):
    current = visible(table)
    choice = action.get("choice")
    if seat not in table["seats"] or action.get("scene") != current["id"]:
        return E.fail(table, "Эта страница уже перевёрнута. Сверьтесь с общей сценой.")
    options = {opt["id"]: opt["label"] for opt in current["choices"]}
    if not isinstance(choice, str) or choice not in options:
        return E.fail(table, "Этот выбор сейчас недоступен.")
    s = table.setdefault("story", initial(table))
    page, party = s["page"], table["party"]
    next_page, after = "", options[choice]
    closes_chapter = page in ("bell", "copies", "gate", "original", "verdict")
    if closes_chapter:
        stamp = E.campaign_stamp(table, seat)
        before = chapter_totals(party)

    if page == "retry" and choice == "work":
        add_day(table)
        party["rested"] = True
        for hid in E.claimed(table):
            hero = table["heroes"][hid]
            hero["hp"], hero["sparks"] = hero["maxHp"], hero["maxSparks"]
            hero["conditions"] = []
        next_page = "retry"
    elif page in ("prologue", "gateRoad", "heartRoad", "retry"):
        result = begin_battle(table, seat, page)
        if not result["ok"]:
            return result
        if page == "retry":
            if party["silver"] >= 2:
                party["silver"] -= 2
            else:
                add_day(table)
        next_page = {"prologue": "bell", "gateRoad": "gate", "heartRoad": "heart", "retry": "heart"}[page]
    elif page == "bell":
        if choice.startswith("song-"):
            singer = choice.removeprefix("song-")
            table["heroes"][singer]["potions"].remove("I19")
            choice = "song"
        finish_field(table, seat, choice != "empty", "bell")
        if choice == "empty":
            E.add_tide(table, 1)
            clue(party, "медная крошка")
        else:
            E.reward(table, seat, {"kind":"prologue"})
            local_glory(party, 1)
            if choice == "tongue":
                clue(party, "медь")
            else:
                party["street"] += 1
        party["chapter"], next_page = 2, "records"
    elif page == "records":
        area = party["realm"]
        if choice == "wall":
            add_day(table)
        name = WITNESSES[area][1]
        if choice == "testimony":
            seal(table)
        s["records"].append({"realm": area, "clue": name, "questReward": choice in ("testimony", "paid")})
        clue(party, name)
        after = f"{E.realms[area-1][0]}. {name.capitalize()}. " + options[choice] + "."
        next_page = "copies" if len(s["records"]) == 2 else "records"
    elif page == "copies":
        if choice == "families":
            party["street"] += 1
        elif choice == "hidden":
            party["silver"] += 3
        else:
            local_glory(party, party["realm"])
        # Closing this chapter overlaps only the scene of the second testimony.
        if not s["records"][-1]["questReward"]:
            seal(table)
        party["chapter"], next_page = 3, "gateRoad"
    elif page == "gate":
        victory = choice in ("hold", "parley")
        finish_field(table, seat, victory, "siege")
        if victory:
            local_glory(party, 6)
            clue(party, "знак гарнизона")
            E.reward(table, seat, {"kind":"normal"})
        else:
            party["suspicion"] = min(4, party["suspicion"]+1)
            add_day(table)
            if choice in ("lada", "boats"):
                clue(party, "свидетельство Лады")
            if choice in ("wagon", "boats"):
                party["supplies"] = min(6, party["supplies"]+3)
            if choice == "boats":
                after = "Ворота пали. Фен забрал Ладу в первую лодку, погонщики перенесли три припаса во вторую. На слушание вместе придут Лада и возница."
        seal(table)
        party["chapter"], next_page = 4, "courtRoad"
    elif page == "courtRoad":
        next_page = "hearing"
    elif page == "hearing":
        if choice == "square":
            add_day(table)
        if choice == "widows":
            party["street"] += 1
            after = "Берта распорола передник на глазах у Эйры. Каждая вдова положила бирку на стол и сама назвала мужа. Их показания вошли в протокол. Отряд получил голос улицы."
        if choice == "serve":
            if party["glory"][0] >= 3:
                s["knighted"] = True
                after = "Эйра приняла присягу. Отряд посвящён в рыцари Вельна."
            else:
                local_glory(party, 1)
                after = "Эйра назначила отряд временными послами. Слава Вельна +1."
        next_page = "council" if choice == "council" else "original"
    elif page == "council":
        if choice == "uncovered":
            party["street"] += 1
            after += ". Выберите на столе приглашение к любой короне или погашение одного долга."
        else:
            s["knighted"] = False
            after += ". Сокамерник спрятал ключ в корке хлеба. Слушание продолжается."
        next_page = "original"
    elif page == "original":
        if choice == "street":
            party["street"] += 1
        elif choice == "keep":
            party["flags"].append("cancelKeeperSignal")
        seal(table)
        party["chapter"], next_page = 5, "heartRoad"
    elif page == "heart" and choice == "altar":
        table["scene"]["keeperBound"] = False
        next_page = "heart"
        after = "Первый набор снят с алтаря. Хранитель теперь может покинуть затвор."
    elif page == "heart" and choice == "silence":
        s["usedSilence"] = True
        next_page = "heart"
        after = "Камертон Эра снял один сигнал Хранителя. Пропустите его эффект на поле. В наступившей тишине с последней скамьи впервые слышно дыхание."
    elif page == "heart" and choice == "cancel":
        party["flags"].remove("cancelKeeperSignal")
        next_page = "heart"
        after = "Печать на оригинале раскололась. Пропустите текущий сигнал Хранителя."
    elif page == "heart":
        finish_field(table, seat, choice != "retreat", "dungeon")
        if choice != "retreat":
            seal(table)
        next_page = "retry" if choice == "retreat" else "verdict"
    elif page == "verdict":
        roadside.deliver(table, seat, s, epilogue=True)
        s["ending"], reason = verdict_result(s, party, choice)
        s["verdictReceipt"] = {"choice": options[choice], "title": E.endings[s["ending"]][0],
                               "reason": reason, "when": stamp}
        s["postscript"] = postscript(s, party)
        next_page = "epilogue"

    promises.close_window(table, seat, s, page)
    if page != "records":
        s["decisions"][page] = choice
    s["page"] = next_page
    if party["chapter"] != current["chapter"]:
        roadside.deliver(table, seat, s)
    if closes_chapter:
        totals = chapter_totals(party)
        s.setdefault("milestones", []).append({"when": stamp, "title": current["title"],
            "choice": action["choice"], "label": options[action["choice"]], "result": after,
            "changes": [{"name": name, "before": start, "after": totals[name]}
                        for name, start in before.items() if totals[name] != start]})
    # Retries of the final encounter can be played indefinitely; the chronicle stays bounded.
    s["history"] = (s["history"] + [{"title": current["title"], "text": after}])[-32:]
    E.log(table, seat, "gm", after + " · " + visible(table)["title"])
    return {"ok": True}
