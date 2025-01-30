var canvasWidth = 1000;
var canvasHeight = 600;

// Removes the item from the array, and throws an error if the item does not 
// exist. 
function arrayRemove(arr, item) {
    const idx = arr.indexOf(item); 
    if (idx == -1) 
        throw new Error("Attempting to remove missing item from array");
    arr.splice(idx, 1);
}

// Returns the time in seconds. 
function timeSeconds() {
    return new Date().getTime() / 1000; 
}

// A list of each puzzle in this level. The puzzle at the front is the current
// puzzle, and every puzzle afterwards has not been shown or activated yet.
var puzzle_template = `[
    new Puzzle(
        "images/field.jpg", 
        400, 400, 
        50, 50, 
        "3x3/", 
        "#ccff99", 
        Piece.MovementType.Stationary
    ), 
    new Puzzle(
        "images/dog.jpg", 
        375, 375, 
        50, 50, 
        "3x3/", 
        "#ffffcc", 
        Piece.MovementType.Needle
    ), 
    new Puzzle(
        "images/night.jpg", 
        300, 300, 
        100, 100, 
        "3x3/", 
        "#9933ff", 
        Piece.MovementType.Gravity 
    ), 
    new Puzzle( 
        "images/building.jpg", 
        425, 425, 
        50, 50, 
        "3x3/",
        "#33cccc",
        Piece.MovementType.Taffy
    ),
    new Puzzle( 
        "images/quantum.jpg", 
        350, 350, 
        100, 100, 
        "3x3/",
        "#ffcccc",
        Piece.MovementType.Circular
    ),
    new Puzzle( 
        "images/train.jpg", 
        250, 250, 
        100, 100, 
        "3x3/",
        "#006600",
        Piece.MovementType.Blink
    ),
    new Puzzle( 
        "images/engine.jpg", 
        400, 400, 
        50, 50, 
        "3x3/", 
        "#800000", 
        Piece.MovementType.Wrap 
    ) 
];`
var puzzles = null;  

// An array holding the active pieces the player can move around and interact
// with. These should only be roots. 
var pieces = null;  

// On the transition between levels, we want to fling the old puzzle out of 
// the canvas and bring the new puzzle pieces on screen. The old pieces will 
// be stored in this array so the new pieces can stay in the (pieces) array. 
// The (oldPieces) array will only have values during (GameState.Loading) and 
// (GameState.Stalled). 
var oldPieces = null; 

// Four possible game states: "playing" (pieces are on the board, player can 
// interact with them), "stalling" (pieces are actively being cleared, no 
// interaction allowed), "loading" (pieces are being generated so we should 
// not update them), and "starting" (the game was just opened but nothing 
// should happen).
const GameState = Object.freeze({
    Starting: Symbol("starting"),
    Playing: Symbol("playing"), 
    Stalling: Symbol("stalling"), 
    Loading: Symbol("loading"), 
    Done: Symbol("done")
})
var gameState = GameState.Starting; 
var stateTime = 0; // The time the program was at when the state changed. 

let button = document.getElementById("button"); 
let scoreText = document.getElementById("score"); 
let timeText = document.getElementById("time"); 
let previousBestTime = null; 
button.addEventListener("click", ()=>{
    gameState = GameState.Loading;
    scoreText.innerText = "Best time: " + 
        (previousBestTime == null ? "none" : previousBestTime);
    puzzles = eval(puzzle_template); 
    puzzles[0].load();
    gameCanvas.gameTime = timeSeconds(); 
});  

var gameCanvas = {
    canvas: document.createElement("canvas"),
    start: function() {
        this.canvas.width = canvasWidth;
        this.canvas.height = canvasHeight;
        ctx = this.canvas.getContext("2d"); 
        this.context = ctx;
        document.body.insertBefore(this.canvas, document.body.childNodes[0]); 
        this.lastTime = timeSeconds();
        this.gameTime = 0; 
    }
}

function startGame() {
    gameCanvas.start();
    setInterval(updateCanvas, 20);  
}

function updateCanvas() {
    console.log(gameState.toString()); 

    ctx = gameCanvas.context; 
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);

    // This is special from the rest of the states. 
    if (gameState == GameState.Starting) {
        ctx.font = "75px Arial"; 
        ctx.fillText("SUPER PUZZLE", 50, 100); 
        ctx.font = "30px Arial"; 
        ctx.fillText("Use your mouse to complete puzzles. Get the best time!", 
            50, 150); 
        ctx.fillText("Click the \"Start Game\" button in the bottom-left " + 
            "to begin.", 50, 200); 
        return; 
    }
    else if (gameState == GameState.Done) {
        let time = Math.round(
            (gameCanvas.finishTime - gameCanvas.gameTime) * 1000) / 1000; 

        ctx.font = "50px Arial"; 
        ctx.fillText("Time: " + time + "s", 50, 100); 
        ctx.font = "30px Arial"; 
        ctx.fillText("Click \"Start Game\" to play again for a faster time!", 
            50, 150); 
        return; 
    }

    var currentTime = timeSeconds();
    var deltaTime = currentTime - gameCanvas.lastTime; 
    gameCanvas.lastTime = currentTime;

    timeText.innerText = "Time: " + 
        Math.round((currentTime - gameCanvas.gameTime) * 1000) / 1000 + 
        "s"

    if (gameState == GameState.Playing && pieces.length == 1) {
        // The puzzle has been completed, so load the next puzzle. 
        gameState = GameState.Loading; 
        stateTime = timeSeconds(); 
        oldPieces = pieces;
        oldPieces[0].movementType = Piece.MovementType.Fling; 
        oldPieces[0].vx = 1000;
        oldPieces[0].vy = 500; 
        oldPieces[0].draw(ctx);
        
        puzzles.shift(); 
        if (puzzles.length == 0) {
            gameState = GameState.Done;
            oldPieces = null;
            gameCanvas.finishTime = timeSeconds();
            let time = Math.round(
                (gameCanvas.finishTime - gameCanvas.gameTime) * 1000) / 1000; 
            if (time < previousBestTime || previousBestTime == null) {
                previousBestTime = time; 
                scoreText.innerText = "Best time: " + 
                    (previousBestTime == null ? "none" : previousBestTime) + 
                    "s";
            }
        } 
        else 
            puzzles[0].load(); 

        return; 
    }
    else if (gameState == GameState.Stalling) {
        // Two situations: (1) this is the first level so just immediately 
        // start the game, or (2) this is not the first level so there are 
        // old pieces on the board that need to be moved. We transition from 
        // Stalled to Playing after some amount of time passed.
        if (oldPieces == null) {
            // Situation (1), just change states.  
            stateTime = timeSeconds(); 
            gameState = GameState.Playing; 
        }
        else {
            // This is situation (2), so we actually need to do something.
            oldPieces[0].update(deltaTime);  
            oldPieces[0].draw(ctx); 
            if (timeSeconds() - stateTime > 5) {
                oldPieces = null; 
                stateTime = timeSeconds(); 
                gameState = GameState.Playing; 
            }
        }
    }

    // Make sure the promise of initializing each piece was fufilled. 
    else if (gameState == GameState.Loading || gameState == GameState.Starting)
        return; 
 
    for (let i = 0; i < pieces.length; i++)
        pieces[i].update(deltaTime); 

    for (let i = 0; i < pieces.length; i++) 
        pieces[i].draw(ctx); 
}

focusedPiece = null; 
prevMousePosition = [0, 0];
prevMouseDirection = [0, 0]; 

// Returns a tuple [x, y] representing the position of the mouse relative to
// the canvas. 
function getMousePosition(mouseEvent) {
    const rect = gameCanvas.canvas.getBoundingClientRect(); 
    const x = mouseEvent.clientX - rect.left; 
    const y = mouseEvent.clientY - rect.top;
    return [x, y]; 
}

document.body.onmousedown = function(e) {
    if (gameState == GameState.Stalled || 
        gameState == GameState.Starting || 
        gameState == GameState.Loading) 
        return; 

    const [x, y] = getMousePosition(e); 
    
    // Look for overlapping pieces from the top (most visible) to the bottom
    // (least visible, below other pieces) of the draw-stack. 
    for (let i = pieces.length - 1; i >= 0; i--) {
        if (pieces[i].isOverlap(x, y)) { 
            focusedPiece = pieces[i]; 
            focusedPiece.isFocused = true; 
            prevMousePosition = [x, y]; 
            
            // Put the element at the bottom of the draw-stack so it's drawn on
            // the top of the screen.
            pieces.splice(i, 1); 
            pieces.push(focusedPiece); 
            
            // Prevent the piece from moving while you're holding it. 
            focusedPiece.vx = 0; 
            focusedPiece.vy = 0; 

            // Only one thing can be clicked at once.
            break; 
        }
    } 
}

document.body.onmouseup = function(e) {
    if (gameState == GameState.Stalled || GameState == GameState.Starting) 
        return; 

    if (focusedPiece != null) {
        focusedPiece.attemptConnect();  

        // Give the piece a velocity in the direction of the mouse movement. 
        if (focusedPiece.movementType != Piece.MovementType.Blink) 
            focusedPiece.generateVelocity(); 
        // const vel = Math.random() * 25; 
        // focusedPiece.vx = prevMouseDirection[0] * vel;
        // focusedPiece.vy = prevMouseDirection[1] * vel; 
        
        focusedPiece.isFocused = false; 
        focusedPiece = null; 
    } 
}

document.body.onmousemove = function(e) {
    if (gameState == GameState.Stalled || GameState == GameState.Starting) 
        return; 

    if (focusedPiece != null) {
        const [x, y] = getMousePosition(e); 
        const [dx, dy] = [x - prevMousePosition[0], y - prevMousePosition[1]]; 
        prevMousePosition = [x, y]; 
        focusedPiece.move(dx, dy); 
        
        let mag = Math.sqrt(Math.pow(dx, 2) + Math.pow(dy, 2)); 
        if (mag == 0) mag = 0.0001; 
        prevMouseDirection = [dx / mag, dy / mag]; 
    }
}
