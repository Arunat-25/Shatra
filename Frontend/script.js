/*let BoardLikeDict = {
    1: 'черная шатра',
    2: 'черная шатра',
    3: 'черная шатра',
    4: 'черная шатра',
    5: 'черная шатра',
    6: 'черная шатра',
    7: 'черная шатра',
    8: 'черная шатра',
    9: 'черная шатра',
    10: 'черный бий',
    11: 'черная шатра',
    12: 'черная шатра',
    13: 'черная шатра',
    14: 'черная шатра',
    15: 'черная шатра',
    16: 'черная шатра',
    17: 'черная шатра',
    18: 'черная шатра',
    19: 'черная шатра',
    20: 'черная шатра',
    21: 'черная шатра',
    22: 'черная шатра',
    23: 'черная шатра',
    24: 'черная шатра',
    25: null,
    26: null,
    27: null,
    28: null,
    29: null,
    30: null,
    31: null,
    32: null,
    33: null,
    34: null,
    35: null,
    36: null,
    37: null,
    38: null,
    39: 'белая шатра',
    40: 'белая шатра',
    41: 'белая шатра',
    42: 'белая шатра',
    43: 'белая шатра',
    44: 'белая шатра',
    45: 'белая шатра',
    46: 'белая шатра',
    47: 'белая шатра',
    48: 'белая шатра',
    49: 'белая шатра',
    50: 'белая шатра',
    51: 'белая шатра',
    52: 'белая шатра',
    53: 'белый бий',
    54: 'белая шатра',
    55: 'белая шатра',
    56: 'белая шатра',
    57: 'белая шатра',
    58: 'белая шатра',
    59: 'белая шатра',
    60: 'белая шатра',
    61: 'белая шатра',
    62: 'белая шатра',
}*/

let BoardLikeDict = {
    1: 'черная шатра',
    2: 'черная шатра',
    3: 'черная шатра',
    4: 'черная шатра',
    5: 'черная шатра',
    6: 'черная шатра',
    7: null,
    8: null,
    9: null,
    10: 'белая шатра',
    11: null,
    12: null,
    13: null,
    14: null,
    15: null,
    16: null,
    17: 'черный батыр',
    18: null,
    19: null,
    20: 'черный бий',
    21: null,
    22: null,
    23: null,
    24: null,
    25: null,
    26: 'черная шатра',
    27: null,
    28: null,
    29: null,
    30: 'черная шатра',
    31: null,
    32: null,
    33: null,
    34: null,
    35: null,
    36: null,
    37: null,
    38: null,
    39: 'белый батыр',
    40: null,
    41: null,
    42: null,
    43: null,
    44: null,
    45: null,
    46: null,
    47: null,
    48: 'белая шатра',
    49: null,
    50: null,
    51: null,
    52: 'белый бий',
    53: 'черная шатра',
    54: null,
    55: null,
    56: null,
    57: 'белая шатра',
    58: 'белая шатра',
    59: 'белая шатра',
    60: 'белая шатра',
    61: 'белая шатра',
    62: 'белая шатра',
}

let my_color = null;
let movers_color = 'белый';
let position_for_mandatory_capture = null;
let opportunity_pass_the_move = false;

/*let movers_color;
let my_color;
let position_for_mandatory_capture = null;*/

function DrawBoard(board) {
    for (let id = 1; id < 63; id++) {
        let element = document.getElementById("position" + id);
        if (board[id] === "черная шатра") {
            element.innerHTML = `${id}<div class="image-in-kletka"><img src="img/черная_точка.png" alt=""></div>`;
        } else if (board[id] === "белая шатра") {
            element.innerHTML = `${id}<div class="image-in-kletka"><img src="img/белая_точка.png" alt=""></div>`;
        }else if (board[id] === "белый бий") {
            element.innerHTML = `${id}<div class="image-in-kletka"><img src="img/белый_бий.png" alt=""></div>`;
        }else if (board[id] === "черный бий") {
            element.innerHTML = `${id}<div class="image-in-kletka"><img src="img/черный_бий.png" alt=""></div>`;
        }else if (board[id] === "белый батыр") {
            element.innerHTML = `${id}<div class="image-in-kletka"><img src="img/белый_батыр.png" alt=""></div>`;
        }else if (board[id] === "черный батыр") {
            element.innerHTML = `${id}<div class="image-in-kletka"><img src="img/черный_батыр.png" alt=""></div>`;
        }
        else{
            element.innerHTML = `${id}`;
        }
    }
}
DrawBoard(BoardLikeDict);

function drawCapturedPieces(list_with_captured_pieces){
    for (let i = 0; i < list_with_captured_pieces.length; i++){
        let id = list_with_captured_pieces[i];
        let element = document.getElementById("position" + id);
        element.innerHTML = `${id}<div class="image-in-kletka"><img src="img/битая_фигра.png" alt=""></div>`;
    }
}

function drawEssentialPositions(allowed_positions){
    for (let i = 0; i < allowed_positions.length; i++){
        let id = allowed_positions[i];
        let element = document.getElementById("position" + id);
        element.innerHTML = `${id}<div class="image-in-kletka"><img src="img/возможные ходы.png" alt=""></div>`;
    }
}

let ws = new WebSocket("ws://localhost:8001/ws/1/"); /* срабатывает каждый раз при получении от сервера*/
ws.onmessage = function (event){
    let data = JSON.parse(event.data);
    console.log("data", data);
    if ("opportunity_pass_the_move" in data){
        let elementButtonPassTheMove = document.getElementById("button_pass_the_move");
        elementButtonPassTheMove.innerHTML = '<button>Передать ход</button>';
    }
    else{
        let elementButtonPassTheMove = document.getElementById("button_pass_the_move");
        elementButtonPassTheMove.innerHTML = '';
    }

    if (data.players_color && data.movers_color){
        my_color = data.players_color;
        movers_color = data.movers_color;
        let element = document.getElementById("my_color");
        element.innerHTML = `my_color is ${my_color}`;
    }

    if (data.essential_positions){ /*если получены разрешенные для взятия позиции и список со взятыми фигурами*/
        if (data.captured_pieces.length !== 0){
            drawCapturedPieces(data.captured_pieces);
        }

        let elementEssentialPositions = document.getElementById("essential_positions");
        elementEssentialPositions.innerHTML = `${data.essential_positions}`;
        drawEssentialPositions(data.essential_positions);
    }else{
        if (data.desk){
            DrawBoard(data.desk);
            BoardLikeDict = data.desk;
            movers_color = data.movers_color;
            position_for_mandatory_capture = data.position_for_mandatory_capture;
            showMessageAndWhoMover(data["message"], movers_color);
        }
    }
}

function sendJSON(){
    let data = {"move_from": move_from, "move_to": move_to, "movers_color": movers_color, "board": BoardLikeDict, "position_for_mandatory_capture": position_for_mandatory_capture};
    ws.send(JSON.stringify(data));
}
function sendPositionMoversColor(chosen_position){
    let data = {"board": BoardLikeDict, "position": chosen_position, "movers_color": movers_color, "position_for_mandatory_capture": position_for_mandatory_capture};
    ws.send(JSON.stringify(data))
}
function showMessageAndWhoMover(message, who_mover){
    let elementWhoMover = document.getElementById("who_mover");
    let elementMessage = document.getElementById("message");
    elementWhoMover.innerHTML = `${who_mover}`;
    elementMessage.innerHTML = `${message}`;
}


let move_from = null;
let move_to = null;


document.querySelector('.board').addEventListener('click', function(event) {

    if (movers_color === my_color && event.target.id.slice(0, 8) === 'position') {
        if (move_from === null && my_color === get_color_of_piece(event.target.id)) {
            move_from = event.target.id;
            if (BoardLikeDict[extractNumberFromPositionString(move_from)] !== null){
                sendPositionMoversColor(move_from);
            }else{
                move_from = null;
            }
            document.getElementById(move_from).classList.add('highlight-black'); // добавляет стиль, написанный в css файле
        } else if (move_from === event.target.id){
            document.getElementById(move_from).classList.remove('highlight-black'); //удаляет примененный стиль для тега с if move_from
            move_from = null;
        } else if (move_from !== null) {
            move_to = event.target.id;
            opportunity_pass_the_move = false; /*СТРАННО НАДО ОБРАТИТЬ ВНИМАНИЕ*/
            sendJSON();
            document.getElementById(move_from).classList.remove('highlight-black');
            move_from = null;
        }
    }
});

function sendZeroToPassTheMove(){
    let data = {"move_from": "position0", "move_to": "position0", "movers_color": movers_color, "board": BoardLikeDict, "position_for_mandatory_capture": position_for_mandatory_capture}; /*скидываем position0 потому что на сервере функция change ожидает такой вид*/
    ws.send(JSON.stringify(data));
}

document.querySelector('#button_pass_the_move').addEventListener('click', function(event) {
    opportunity_pass_the_move = false;
    sendZeroToPassTheMove()
});

function extractNumberFromPositionString(str) {
    // Используем регулярное выражение для извлечения числа
    const match = str.match(/position(\d+)/);
    if (match) {
        // Преобразуем извлеченное число в целое число
        return parseInt(match[1], 10);
    }
    // Если строка не соответствует ожидаемому формату, возвращаем null или другое значение по умолчанию
    return null;
}

function get_color_of_piece(position){ // принимает строку например position12, position39 ...
    let color_of_piece;
    if (BoardLikeDict[extractNumberFromPositionString(position)] !== null && BoardLikeDict[extractNumberFromPositionString(position)].includes("бел")){
        color_of_piece = "белый";
    } else if (BoardLikeDict[extractNumberFromPositionString(position)] !== null && BoardLikeDict[extractNumberFromPositionString(position)].includes("чер")){
        color_of_piece = "черный";
    } else{
        color_of_piece = null;
    }
    return color_of_piece;
}