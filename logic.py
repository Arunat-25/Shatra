from словари import (black_shatra_possible_moves,
                     white_shatra_possible_moves,
                     shatra_and_biy_possible_captures,
                     black_biy_possible_moves,
                     white_biy_possible_moves,
                     batyr_moves_and_captures,)


# функция для определения вида фигуры по его позиции на доске
def piece_type(positions, piece_position):
    if positions[piece_position] is None:
        return ''
    piece_name = positions[piece_position]
    if 'шатра' in piece_name:
        return 'шатра'
    elif 'бий' in piece_name:
        return 'бий'
    elif 'батыр' in piece_name:
        return 'батыр'


# функция для определения цвета фигуры по его позиции на доске
def piece_color(positions, piece_position):
    if positions[piece_position] is None:
        return ''
    piece_name = positions[piece_position]
    if 'бел' in piece_name:
        return 'белый'
    else:
        return 'черный'

def can_piece_enter_in_fortress(positions, chosen_piece_position, target_position): # надо дописать чтобы шатра могла брать фигуру в крепости, даже если есть свои шатры
    color_of_chosen_piece = piece_color(positions, chosen_piece_position)
    if color_of_chosen_piece == 'белый' and target_position in range(53, 63) and not (chosen_piece_position in range(53, 63)):
        for i in range(53, 63):
            if positions[i] == 'белая шатра':
                return False
        return True
    elif color_of_chosen_piece == 'белый' and target_position in range(53, 63) and chosen_piece_position in range(53, 63):
        opponent_piece_position = shatra_and_biy_possible_captures[chosen_piece_position][target_position]
        opponent_piece_color = piece_color(positions, opponent_piece_position)
        if opponent_piece_color == 'черный':
            return True
        return False
    elif color_of_chosen_piece == 'черный' and target_position in range(1, 11) and not (chosen_piece_position in range(1, 11)):
        for i in range(1, 11):
            if positions[i] == 'черная шатра':
                return False
        return True
    elif color_of_chosen_piece == 'черный' and target_position in range(1, 11) and chosen_piece_position in range(1, 11):
        opponent_piece_position = shatra_and_biy_possible_captures[chosen_piece_position][target_position]
        opponent_piece_color = piece_color(positions, opponent_piece_position)
        if opponent_piece_color == 'белый':
            return True
        return False
    return True

# функции, проверяющие
# возможен ли ход выбранной шатра, если возможно то ходит
def move_of_shatra(positions, chosen_piece_position, target_position):
    color_chosen_piece = piece_color(positions, chosen_piece_position)

    if color_chosen_piece == 'черный' and  positions[target_position] is None and target_position in black_shatra_possible_moves[chosen_piece_position]:

        if 1 <= chosen_piece_position <= 8:
            can_shatrta_move = True
            for position in range(-9, -chosen_piece_position):
                position = abs(position)
                if piece_color(positions, position) == 'черный':
                    can_shatrta_move = False
                    break
            if can_shatrta_move:
                positions[target_position] = positions[chosen_piece_position]
                positions[chosen_piece_position] = None
                return True
            return False

        else:
            if target_position in [60, 61, 62]:
                positions[target_position] = 'черный батыр'
                positions[chosen_piece_position] = None
                return True
            else:
                positions[target_position] = positions[chosen_piece_position]
                positions[chosen_piece_position] = None
                return True

    elif color_chosen_piece == 'белый' and  positions[target_position] is None and target_position in white_shatra_possible_moves[chosen_piece_position]:

        if 54 <= chosen_piece_position <= 62:
            can_shatrta_move = True
            for position in range(54, chosen_piece_position):
                if piece_color(positions, position) == 'белый':
                    can_shatrta_move = False
                    break
            if can_shatrta_move:
                positions[target_position] = positions[chosen_piece_position]
                positions[chosen_piece_position] = None
                return True
            return False

        else:
            if target_position in [1, 2, 3]:
                positions[target_position] = 'белый батыр'
                positions[chosen_piece_position] = None
                return True
            else:
                positions[target_position] = positions[chosen_piece_position]
                positions[chosen_piece_position] = None
                return True
    return False

# функция проверяющая ход для бия
def move_of_biy(positions, chosen_piece_position, target_position):
    color_chosen_piece = piece_color(positions, chosen_piece_position) # сохраняем в переменную цвет фигуры, выбранной для хода
    if positions[target_position] is not None: # если позиция в которую ходят не пуста
        return False # вернуть False
    else: # а если позиция в которую ходят пуста
        if color_chosen_piece == 'черный': # если ходят черные
            if 1 <= target_position <= 9: # если черные ходят на позицию от 1 до 9
                can_biy_move = True #
                for piece in range(1, 10):
                    if piece_type(positions, piece) == 'шатра' and piece_color(positions, piece) == 'черный':
                        can_biy_move = False
                        break
                if can_biy_move and target_position in black_biy_possible_moves[chosen_piece_position]:
                    positions[target_position] = positions[chosen_piece_position]
                    positions[chosen_piece_position] = None
                    return True
                else:
                    return False

            elif target_position in black_biy_possible_moves[chosen_piece_position]:
                positions[target_position] = positions[chosen_piece_position]
                positions[chosen_piece_position] = None
                return True
            return False

        elif color_chosen_piece == 'белый':
            if 54 <= target_position <= 62:
                can_biy_move = True
                for piece in range(54, 63):
                    if piece_type(positions, piece) == 'шатра' and piece_color(positions, piece) == 'белый':
                        can_biy_move = False
                        break

                if can_biy_move and target_position in white_biy_possible_moves[chosen_piece_position]:
                    positions[target_position] = positions[chosen_piece_position]
                    positions[chosen_piece_position] = None
                    return True
                else:
                    return False

            elif target_position in white_biy_possible_moves[chosen_piece_position]:
                positions[target_position] = positions[chosen_piece_position]
                positions[chosen_piece_position] = None
                return True

# функция для определения можно ли взять шатрой или бием другую фигуру
def capture_of_shatra_and_biy(positions, chosen_piece_position, target_position):
    color_chosen_piece = piece_color(positions, chosen_piece_position)
    opponent_piece_position = shatra_and_biy_possible_captures.get(chosen_piece_position).get(target_position)
    if opponent_piece_position is None:
        return False
    color_opponent_piece = piece_color(positions, opponent_piece_position)

    if color_chosen_piece == 'черный' and color_opponent_piece == 'белый' and positions[target_position] is None and can_piece_enter_in_fortress(positions, chosen_piece_position, target_position):
        positions[target_position] = positions[chosen_piece_position]
        positions[opponent_piece_position] = None
        positions[chosen_piece_position] = None
        return True
    elif color_chosen_piece == 'белый' and color_opponent_piece == 'черный' and positions[target_position] is None and can_piece_enter_in_fortress(positions, chosen_piece_position, target_position):
        positions[target_position] = positions[chosen_piece_position]
        positions[opponent_piece_position] = None
        positions[chosen_piece_position] = None
        return True
    return False

who_was_captured_by_batyr = []
# функция для проверки хода и взятия батыром
def move_or_capture_of_batyr(positions, chosen_piece_position, target_position):
    color_chosen_piece = piece_color(positions, chosen_piece_position) # сохраняем в переменную цвет фигуры, выбранной для хода
    if positions[target_position] is not None: # если позиция в которую ходят не пуста
        return False # вернуть False
    else: # а если позиция в которую ходят пуста
        if color_chosen_piece == 'черный': # если ходят черные
            if not(can_piece_enter_in_fortress(positions, chosen_piece_position, target_position)): # проверяем батыр ходит ли в свою крепость, если да ходит проверяем есть ли своя шатра, а если не ходит в свою крепость, то true
                return False
            else: # если батыр ходит не в свою крепость
                if chosen_piece_position in range(1, 10) and target_position in range(11, 32): # если батыр выставляется с поля резерва
                    positions[target_position] = positions[chosen_piece_position] # переносим батыра на позицию, в которую был совершен ход
                    positions[chosen_piece_position] = None # убираем с той позиции на которй стоял
                    return True  # возвращаем тру
                for i in range(len(batyr_moves_and_captures[chosen_piece_position])): # начинаем перебирать направления в которые батыр может сходить
                    count_of_pieces_on_the_way = 0 # переменная в которой хранится количество фигур между выбранной позицией для хода и позицией куда ходят
                    position_of_enemy = None # позиция вражеской фигуры между выбранной позицией для хода и позицией куда ходят
                    for j in batyr_moves_and_captures[chosen_piece_position][i]: # начинаем перебирать позиции в направлениях в которые батыр может сходить
                        if j == target_position: # если позиция в иттерации равна позиции в которую ходит батыр
                            if count_of_pieces_on_the_way == 0: # если до позиции куда хочет сходить батыр не встречалась ни одна фигура
                                positions[target_position] = positions[chosen_piece_position] # переносим батыра в позицию куда он хотел сходить
                                positions[chosen_piece_position] = None # а позицию где он стоял очищаем
                                return True # возвращаем true
                            elif count_of_pieces_on_the_way == 1 and position_of_enemy is not None: # если же на пути встречалась одна фигура и это вражеская фигура
                                positions[target_position] = positions[chosen_piece_position] # переносим батыра в позицию куда он хотел сходить
                                positions[chosen_piece_position] = None # а позицию где он стоял очищаем
                                who_was_captured_by_batyr.append(position_of_enemy)
                                positions[position_of_enemy] = None # позицию где стояла вражеская фигура очищаем
                                return True # возвращаем true
                            else: # если на пути больше одной фигуры или своя фигура
                                return False # возврат false
                        elif positions[j] is not None or j in who_was_captured_by_batyr: # если на пути встретилась фигура ,,,, ЗДЕСЬ НАДО ПРОВЕРЯТЬ positions[j] in list со съеденными позициями
                            count_of_pieces_on_the_way += 1 # добавляем 1 к переменной считающей фигуры на пути
                            if piece_color(positions, j) == 'белый': # если эта фигура белая
                                position_of_enemy = j # то переменной хранящей позицию вражеской фигруы передаем этц позицию

        elif color_chosen_piece == 'белый': # если ходят черные
            if not(can_piece_enter_in_fortress(positions, chosen_piece_position, target_position)): # проверяем батыр ходит ли в свою крепость, если да ходит проверяем есть ли своя шатра, а если не ходит в свою крепость, то true
                return False
            else: # если батыр ходит не в свою крепость
                if chosen_piece_position in range(54, 63) and target_position in range(32, 53): # если батыр выставляется с поля резерва
                    positions[target_position] = positions[chosen_piece_position] # переносим батыра на позицию, в которую был совершен ход
                    positions[chosen_piece_position] = None # убираем с той позиции на которй стоял
                    return True # возвращаем тру
                for i in range(len(batyr_moves_and_captures[chosen_piece_position])): # начинаем перебирать направления в которые батыр может сходить
                    count_of_pieces_on_the_way = 0 # переменная в которой хранится количество фигур между выбранной позицией для хода и позицией куда ходят
                    position_of_enemy = None # позиция вражеской фигуры между выбранной позицией для хода и позицией куда ходят
                    for j in batyr_moves_and_captures[chosen_piece_position][i]: # начинаем перебирать позиции в направлениях в которые батыр может сходить
                        if j == target_position: # если позиция в иттерации равна позиции в которую ходит батыр
                            if count_of_pieces_on_the_way == 0: # если до позиции куда хочет сходить батыр не встречалась ни одна фигура
                                positions[target_position] = positions[chosen_piece_position] # переносим батыра в позицию куда он хотел сходить
                                positions[chosen_piece_position] = None # а позицию где он стоял очищаем
                                return True # возвращаем true
                            elif count_of_pieces_on_the_way == 1 and position_of_enemy is not None: # если же на пути встречалась одна фигура и это вражеская фигура
                                positions[target_position] = positions[chosen_piece_position] # переносим батыра в позицию куда он хотел сходить
                                positions[chosen_piece_position] = None # а позицию где он стоял очищаем
                                who_was_captured_by_batyr.append(position_of_enemy)
                                positions[position_of_enemy] = None # позицию где стояла вражеская фигура очищаем
                                return True # возвращаем true
                            else:  # если на пути больше одной фигуры или своя фигура
                                return False # возврат false
                        elif positions[j] is not None or j in who_was_captured_by_batyr: # если на пути встретилась фигура или подвергшаяся взятию (в этом же ходе, то есть пока ход не передан другому игроку)
                            count_of_pieces_on_the_way += 1 # добавляем 1 к переменной считающей фигуры на пути
                            if piece_color(positions, j) == 'черный': # если эта фигура черная
                                position_of_enemy = j # то переменной хранящей позицию вражеской фигруы передаем этц позицию


history_of_positions = []
# функция проверяет на конец игры: если нет одного бия или позиция повторилась 3 раза, то конец игры
def is_game_over(positions):
    # проверка количества биев на доске, если он один, то игра заканчивается
    count_of_biy = 0
    name_of_alive_biy = ''
    for position_of_piece, name_of_piece in positions.items():
        if name_of_piece is not None and 'бий' in name_of_piece:
            count_of_biy += 1
            name_of_alive_biy = name_of_piece
    if count_of_biy == 1:
        text = f'{name_of_alive_biy} победил!'
        return [True, text]
    # проверка на повторение ходов, если позиция встречается три раза за игру, то ничья
    if len(history_of_positions) > 0:
        if history_of_positions[-1] != str(positions):
            history_of_positions.append(str(positions))
    elif len(history_of_positions) == 0:
        history_of_positions.append(str(positions))
    if history_of_positions.count(str(positions)) == 3:
        show_desk(positions)
        text = 'Ничья! Позиция повторилась три раза.'
        return [True, text]
    return [False]



# функция возвращает список с ходами, которые показывают объязательное(-ые) взятие(-я) шатрой или батыром
def mandatory_captures(desk, color_of_mover):
    opposite_color_of_mover = 'черный' if color_of_mover == 'белый' else 'белый' #передаем ход

    positions_and_target_position_of_pieces_for_move = []
    for position in desk:
        if color_of_mover == piece_color(desk, position):
            if piece_type(desk, position) == 'шатра' or piece_type(desk, position) == 'бий':
                for possible_target_position in shatra_and_biy_possible_captures[position]:
                    possible_enemy_position = shatra_and_biy_possible_captures[position][possible_target_position]
                    if piece_color(desk, possible_enemy_position) == opposite_color_of_mover and desk[possible_target_position] is None and can_piece_enter_in_fortress(desk, position, possible_target_position):
                        positions_and_target_position_of_pieces_for_move.append([position, possible_target_position])
            elif piece_type(desk, position) == 'батыр':
                where_is_enemies = []  # хранятся позиции вражеских фигур, при ходе с батыра
                where_batyr_can_capture = []  # харнятся в какие позиции батыр может совершить взятие

                for direction in batyr_moves_and_captures[position]:  # пробегаемся по направлениям в которые батыр может сходить
                    start_add_positions_where_batyr_can_capture = False  # false стоит когда в where_is_enemies не добалена вражеская фигура в направлении, а когда вражеская фигура, которая может быть съедена, перемнной принимается значение True, и когда стоит True мы можем начинать заполнять where_batyr_can_capture позициями,в которые батыр может съесть фигуру, которую мы добавили в список where_is_enemies
                    for index_of_probably_positions_of_enemy in range(len(direction) - 1):  # пробегаемся индексом по позициям внутри направлений
                        probably_position_of_enemy = direction[index_of_probably_positions_of_enemy]  # по индексу получаем позицию на которой может стоять вражеская фигура
                        probably_next_position_of_enemy = direction[index_of_probably_positions_of_enemy + 1]  # получаем позицию за позицией на которой может стоять вражеская фигура

                        if (desk[probably_position_of_enemy] is not None and desk[probably_next_position_of_enemy] is not None) or (probably_position_of_enemy in who_was_captured_by_batyr):
                            break
                        if piece_color(desk, probably_position_of_enemy) != '': # если стоит фигура на пути иттерации по направлению
                            if piece_color(desk, probably_position_of_enemy) != opposite_color_of_mover: # и эта союзная фигура
                                break # останавливаем эту иттерацию по этому направлению, так как батыр не может перепрыгивать через союзные фигуры
                        if not start_add_positions_where_batyr_can_capture and piece_color(desk, probably_position_of_enemy) == opposite_color_of_mover and desk[probably_next_position_of_enemy] is None and can_piece_enter_in_fortress(desk, position, probably_position_of_enemy):  # если встретившаяся фигура вражеская и за ней нет другой фигуры
                            where_is_enemies.append(probably_position_of_enemy)  # вносим в список вражеских фигур, которые батыр может съесть
                            start_add_positions_where_batyr_can_capture = True  # после добавления вражеской фигуры которая может быть съедена, даем знак, что можно заполнять список позициями, в которые можно съесть батыром
                        if start_add_positions_where_batyr_can_capture:  # если можно начинать заполнять список позициями, в которые можно съесть батыром
                            # probably_position_of_enemy дальше становится переменной, в которой хранится позиция которая рассматривается: туда можно сходить или нет
                            if not (probably_position_of_enemy in where_is_enemies):  # проверяем не на той ли иттерации в которой был дан знак, потому что если на той то нам не нужная позиция этой иттерации, так как на нем стоит вражеская фигура, а нам нужны позиции после(за) этой фигуры(ой)
                                if desk[probably_position_of_enemy] is not None:  # если же после вражеской фигуры, которая может быть съедена, встречается еще одна любая фигура
                                    break  # останавливаем, так как мы батыром не можем сразу две фигуры захватить
                                where_batyr_can_capture.append([position, probably_position_of_enemy])  # добавляем позицию, в список позиций, в которые батыр может съесть
                            if index_of_probably_positions_of_enemy + 1 == len(direction) - 1 and desk[probably_next_position_of_enemy] is None:  # если же последняя иттерация(то есть на предпоследней позиции направления, по которому иттерация), то мы проверяем последнюю позицию пуста ли, и если пуста добавляем в список, в которые батыр может съесть вражескую фигуру
                                where_batyr_can_capture.append([position, probably_next_position_of_enemy])  # добавляем в список относительно предпоследней позиции следующую позицию, то есть последнюю в направлении.
                positions_and_target_position_of_pieces_for_move = positions_and_target_position_of_pieces_for_move + where_batyr_can_capture # добавляем батыровские ходы, в список с позициями в которые можноо совершить объязательное взятие
    return positions_and_target_position_of_pieces_for_move

# функция возвращает список c позициями, на которые можно сходить и при это совершить взятие с позиции, которая предается в параметре
def get_mandatory_capture_for_one_position(position, who_mover):
    essential_captures = []
    for variant in (mandatory_captures(positions, who_mover)):
        if variant[0] == position:
            essential_captures.append(variant[1])
    return essential_captures
def get_mandatory_capture_for_one_position2(positions, position, who_mover):
    essential_captures = []
    for variant in (mandatory_captures(positions, who_mover)):
        if variant[0] == position:
            essential_captures.append(variant[1])
    return essential_captures

# функция возвращает с каких позиций есть обьязательное взятие
def get_mandatory_capture_for_two_positions(positions, who_mover): # функцию назвать на более логичное и сверху тоже
    from_capture = set()
    for variant in (mandatory_captures(positions, who_mover)):
        from_capture.add(variant[0])
    return from_capture

# функция возвращает в какие позиции есть обьязательное взятие
def get_mandatory_capture_for_three_positions(positions, who_mover): # функцию на более логичное и сверху тоже
    to_capture = []
    for variant in (mandatory_captures(positions, who_mover)):
        to_capture.append(variant[1])
    return to_capture


def game_logic(positions, who_mover, chosen_piece_position, target_position, position_for_mandatory_capture):
    information_about_game_over = is_game_over(positions)  # в переменную сохраняется [причина конца игры, статус игры(True- игра не идет, False - идет)
    print(information_about_game_over)
    if information_about_game_over[0]:  # если игра закончилась
        return {'desk': positions, 'movers_color': None, 'message': f"Конец игры! {information_about_game_over[1]}"}


    if position_for_mandatory_capture is not None: # если игрок продолжает взятие
        if piece_type(positions, position_for_mandatory_capture) == 'бий':
            if chosen_piece_position == 0:
                who_mover = 'черный' if who_mover == 'белый' else 'белый'  # передаем ход
                return {'desk': positions, 'movers_color': who_mover, 'message': f"Успешно! теперь ходит {who_mover}", 'position_for_mandatory_capture': None}
            else:
                if position_for_mandatory_capture == chosen_piece_position:
                    chosen_piece_position = position_for_mandatory_capture
                else:
                    return {'desk': positions, 'movers_color': who_mover, 'message': 'Надо продолжить взятие!', "position_for_mandatory_capture": position_for_mandatory_capture}
        elif position_for_mandatory_capture == chosen_piece_position:
            chosen_piece_position = position_for_mandatory_capture
        else:
            return {'desk': positions, 'movers_color': who_mover, 'message': 'Надо продолжить взятие!', "position_for_mandatory_capture": position_for_mandatory_capture}

    mandatory_captures(positions, who_mover)

    if len(get_mandatory_capture_for_two_positions(positions, who_mover)) > 0 and not (chosen_piece_position in get_mandatory_capture_for_two_positions(positions, who_mover)):  # если есть обьязательное взятие, но выбранная фигура не из списка, возвращаемой функцией, которая возвращает список позиций с которых можно совершать взятие
        return {'desk': positions, 'movers_color': who_mover, 'message': 'Надо объязательно брать фигуру соперника 1', "position_for_mandatory_capture": position_for_mandatory_capture}
    elif len(get_mandatory_capture_for_two_positions(positions, who_mover)) == 1 and piece_type(positions, chosen_piece_position) != 'бий' and not (target_position in get_mandatory_capture_for_three_positions(positions, who_mover)):  # если есть обьязательное взятие выбранной для хода фигурой, но игрок пытается не совершать взятие
        return {'desk': positions, 'movers_color': who_mover, 'message': 'Надо объязательно брать  2', "position_for_mandatory_capture": position_for_mandatory_capture}
    elif len(get_mandatory_capture_for_two_positions(positions, who_mover)) > 1 and not (target_position in get_mandatory_capture_for_three_positions(positions, who_mover)):  # если есть обьязательное взятие выбранной для хода фигурой, но игрок пытается не совершать взятие
        return {'desk': positions, 'movers_color': who_mover, 'message': 'Надо объязательно брать  3', "position_for_mandatory_capture": position_for_mandatory_capture}

    else:
        if piece_type(positions, chosen_piece_position) == 'шатра': # если выбранная для хода фигура это шатра
            if capture_of_shatra_and_biy(positions, chosen_piece_position, target_position): # если было проведено взятие
                if len(mandatory_captures(positions, who_mover)) > 0: # если есть объязательное(ые) взятие(я) на доске для игрока, который совершил взятие
                    position_after_capture = target_position # присваиваем позицию на которой стоит шатра после взятия
                    for i in (mandatory_captures(positions, who_mover)): # пробегаемся по всем объязательным взятиям для игрока который ходит
                        if i[0] == position_after_capture: # и если встречается взятие с позиции, где стоит взявшая до этого шатра
                            position_for_mandatory_capture = position_after_capture # позицию фигуры после взятия приравниваем к переменной, которая есть для этого
                            return {'desk': positions, 'movers_color': who_mover, 'message': "Успешно! Надо продолжить взятие!", "position_for_mandatory_capture": position_for_mandatory_capture}
                        elif i == mandatory_captures(positions, who_mover)[-1]: # если цикл прошел по всем обьязательным ходам на доске, но не нашел объзательное взятие для шатры, который уже совершил взятие
                            who_mover = 'черный' if who_mover == 'белый' else 'белый'  # передаем ход
                            return {'desk': positions, 'movers_color': who_mover, 'message': f"Успешно! теперь ходит {who_mover}", "position_for_mandatory_capture": None}
                else: # если нет объязательного взятия после взятия на доске для игрока, который совершил взятие
                    who_mover = 'черный' if who_mover == 'белый' else 'белый'  # передаем ход
                    return {'desk': positions, 'movers_color': who_mover, 'message': f"Успешно! теперь ходит {who_mover}", "position_for_mandatory_capture": None}
            elif move_of_shatra(positions, chosen_piece_position, target_position): # если не было совершенно взятие, но был совершен ход
                who_mover = 'черный' if who_mover == 'белый' else 'белый' #передаем ход
                return {'desk': positions, 'movers_color': who_mover, 'message': f"Успешно! теперь ходит {who_mover}", "position_for_mandatory_capture": None}
            elif not (can_piece_enter_in_fortress(positions, chosen_piece_position, target_position)): # если не сработал ход и взятие из за пешки на своей крепости
                return {'desk': positions, 'movers_color': who_mover, 'message': f"Нельзя брать на свою крепость, т.к. там своя шатра!", "position_for_mandatory_capture": position_for_mandatory_capture}

        elif piece_type(positions, chosen_piece_position) == 'бий': # если же выбранная фигура для хода бий
            if capture_of_shatra_and_biy(positions, chosen_piece_position, target_position): # если бий совершил взятие
                if len(mandatory_captures(positions, who_mover)) > 0:  # если есть объязательное(ые) взятие(я) на доске для игрока, который совершил взятие
                    position_after_capture = target_position  # присваиваем позицию на которой стоит шатра после взятия
                    for i in (mandatory_captures(positions, who_mover)):  # пробегаемся по всем объязательным взятиям для игрока который ходит
                        if i[0] == position_after_capture:  # и если встречается взятие с позиции, где стоит взявшая до этого бий
                            position_for_mandatory_capture = position_after_capture # позиция фигуры после взятия приравниваем к переменной, которая есть для этого
                            return {'desk': positions, 'movers_color': who_mover, 'message': f"Успешно! продолжи взятие или передай ход!", "opportunity_pass_the_move": True, "position_for_mandatory_capture": position_for_mandatory_capture}
                        elif i == mandatory_captures(positions, who_mover)[-1]:  # если цикл прошел по всем обьязательным ходам на доске, но не нашел объзательное взятие для шатры, который уже совершил взятие
                            who_mover = 'черный' if who_mover == 'белый' else 'белый'  # передаем ход
                            return {'desk': positions, 'movers_color': who_mover, 'message': f"Успешно! теперь ходит {who_mover}", "position_for_mandatory_capture": None}
                else: # если нет объязательного взятия после взятия на доске для игрока, который совершил взятие
                    who_mover = 'черный' if who_mover == 'белый' else 'белый' # передаем ход
                    return {'desk': positions, 'movers_color': who_mover, 'message': f"Успешно! теперь ходит {who_mover}", "position_for_mandatory_capture": None}
            elif move_of_biy(positions, chosen_piece_position, target_position): # если бий не совершил взятие, а сходил
                who_mover = 'черный' if who_mover == 'белый' else 'белый'  # передаем ход
                return {'desk': positions, 'movers_color': who_mover, 'message': f"Успешно! теперь ходит {who_mover}", "position_for_mandatory_capture": None}
            elif not(can_piece_enter_in_fortress(positions, chosen_piece_position, target_position)): # если не сработал ход и взятие из за пешки на своей крепости
                return {'desk': positions, 'movers_color': who_mover, 'message': f"Нельзя брать на свою крепость, т.к. там своя шатра!", "position_for_mandatory_capture": position_for_mandatory_capture}

        elif piece_type(positions, chosen_piece_position) == 'батыр':  # если же выбранная фигура для хода батыр
            global who_was_captured_by_batyr
            if move_or_capture_of_batyr(positions, chosen_piece_position, target_position) and len(who_was_captured_by_batyr) > 0: # если батыр совершил взятие или сходил и список со взятыми фигурами не пуст( эти два условия дают - батыр совершил взятие)
                if len(mandatory_captures(positions, who_mover)) > 0:  # если есть объязательное(ые) взятие(я) на доске для игрока, который совершил взятие
                    position_after_capture = target_position  # присваиваем позицию на которой стоит батыр после взятия
                    for i in (mandatory_captures(positions, who_mover)):  # пробегаемся по всем объязательным взятиям для игрока который ходит
                        if i[0] == position_after_capture:  # и если встречается взятие с позиции, где стоит взявший до этого батыр
                            position_for_mandatory_capture = position_after_capture  # позицию фигуры после взятия приравниваем к переменной, которая есть для этого
                            return {'desk': positions, 'movers_color': who_mover, 'message': "Успешно! Надо продолжить взятие!", "position_for_mandatory_capture": position_for_mandatory_capture}
                        elif i == mandatory_captures(positions, who_mover)[-1]:  # если цикл прошел по всем обьязательным ходам на доске, но не нашел объзательное взятие для батыра, который уже совершил взятие
                            who_was_captured_by_batyr = []
                            who_mover = 'черный' if who_mover == 'белый' else 'белый'  # передаем ход
                            return {'desk': positions, 'movers_color': who_mover, 'message': f"Успешно! теперь ходит {who_mover}", "position_for_mandatory_capture": None}
                else:  # если нет объязательного взятия после взятия на доске для игрока, который совершил взятие
                    who_was_captured_by_batyr = []
                    who_mover = 'черный' if who_mover == 'белый' else 'белый'  # передаем ход
                    return {'desk': positions, 'movers_color': who_mover, 'message': f"Успешно! теперь ходит {who_mover}", "position_for_mandatory_capture": None}
                    # надо написать что если есть дальше взятие, то position_for_mandatory_capture = стяощей позии а target_position_after_capture должен быть в where_batyr_can_capture а есои нет взяти то поменять цвет
            else:
                who_mover = 'черный' if who_mover == 'белый' else 'белый'  # передаем ход
                return {'desk': positions, 'movers_color': who_mover, 'message': f"Успешно! теперь ходит {who_mover}", "position_for_mandatory_capture": None}




def send_captured_pieces(positions, chosen_position, position_for_mandatory_capture):
    if chosen_position == position_for_mandatory_capture and piece_type(positions, position_for_mandatory_capture) == 'батыр':
        return who_was_captured_by_batyr
    return []