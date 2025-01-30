// A single puzzle contains a mode for the movement of the pieces, an image, 
// and other things.
class Puzzle { 
    // (puzzleImageSize) is the size of the resulting puzzle on the final
    // screen when it's all put together. (resolutionSize) is the size we 
    // interpolate at in relation to the original image.
    constructor(
        puzzleFileName,
        puzzleImageWidth, 
        puzzleImageHeight, 
        resolutionWidth, 
        resolutionHeight, 
        stencilFolderName, 
        backgroundColor, 
        movementType) 
    { 
        this.puzzleFileName = puzzleFileName; 
        this.puzzleImageWidth = puzzleImageWidth; 
        this.puzzleImageHeight = puzzleImageHeight; 
        this.resolutionWidth = resolutionWidth; 
        this.resolutionHeight = resolutionHeight; 
        this.stencilFolderName = stencilFolderName;  
        this.backgroundColor = backgroundColor; 
        this.movementType = movementType;

        // This will be set later. 
        this.stencilImageWidth = -1; 
        this.stencilImageHeight = -1;
    } 

    // Creates an image with a new size. 
    createImage(ctx, basis, stencil)
    {
        var buffer = new Uint8ClampedArray(
            this.puzzleImageWidth * this.puzzleImageHeight * 4);
        for (let r = 0; r < this.puzzleImageHeight; r++) {
            for (let c = 0; c < this.puzzleImageWidth; c++) {
                // We have a (r, c) coordinate for the new image (that we're 
                // constructing right now). We want to create an associated 
                // (rb, cb) coordinate for the basis image.
                let rb = ((r / this.puzzleImageHeight) * 
                    this.resolutionHeight) | 0; 
                let cb = ((c / this.puzzleImageWidth) * 
                    this.resolutionWidth) | 0; 
    
                // Same for the stencil coordinate. 
                let rs = ((r / this.puzzleImageHeight) * 
                    this.stencilImageHeight) | 0; 
                let cs = ((c / this.puzzleImageWidth) * 
                    this.stencilImageWidth) | 0; 
    
                // Turn this 2D coordinate into a 1D position, taking into 
                // consideration how each pixel is represented by four numbers
                // (r, g, b, a).
                let posNew = (r * this.puzzleImageWidth + c) * 4; 
                let posBasis = (rb * this.resolutionWidth + cb) * 4; 
                let posStencil = (rs * this.stencilImageWidth + cs) * 4; 
               
                buffer[posNew+0] = basis[posBasis+0];
                buffer[posNew+1] = basis[posBasis+1];
                buffer[posNew+2] = basis[posBasis+2];
                buffer[posNew+3] = 
                    stencil[posStencil] >= 128 ?
                    basis[posBasis+3] : 0; 
            }
        }
        
        let imageData = new ImageData(buffer, this.puzzleImageWidth); 
        let bmp = createImageBitmap(imageData);
    
        return bmp; 
    } 
    
    // Initializes the type of level to play now.
    initializeLevel() {
        var canvas = document.createElement("canvas"); 
        canvas.width = 1000; 
        canvas.height = 1000;
        var ctx = canvas.getContext("2d"); 
        
        // Function called when one image loads. (initializeLevel) will load 
        // several images including the image depicted on the puzzle itself and 
        // the image of each stencil. When all images load, this function proceeds.
        let imageLoadCounter = 0; 
        let totalImagesSize = 10; 
        let puzzle = this; 
        function whenLoad() {
            imageLoadCounter += 1;
            if (imageLoadCounter != totalImagesSize) 
                return; 
    
            ctx.drawImage(img, 0, 0);
            let imgData = ctx.getImageData(
                0, 0, puzzle.resolutionWidth, puzzle.resolutionHeight);
            
            puzzle.stencilImageWidth = stencils[0].width; 
            puzzle.stencilImageHeight = stencils[0].height; 

            pieces = new Array(9);
            let promises = new Array(9); 
            for (let i = 0; i < 9; i++) {
                ctx.drawImage(stencils[i], 0, 0); 
                let data = ctx.getImageData(
                    0, 0, puzzle.stencilImageWidth, puzzle.stencilImageHeight); 
                let promise = puzzle.createImage(ctx, imgData.data, data.data)
                .then(function(result) { 
                    const width = puzzle.puzzleImageWidth / 3; 
                    const height = puzzle.puzzleImageHeight / 3; 
                    let row = Math.trunc(i / 3);
                    let col = i % 3; 
                    pieces[i] = new Piece(
                        result, 
                        row, 
                        col, 
                        Math.random() * (canvasWidth - width) - 
                            col * width, 
                        Math.random() * (canvasHeight - height) - 
                            row * height, 
                        width, 
                        height, 
                        puzzle.movementType
                    );
                });
                promises[i] = promise; 
            }
        
            // A list of all the pieces. At this point, the pieces list is 
            // complete. 
            Promise.all(promises).then(function(result) {
                for (let i = 0; i < 9; i++) {
                    let piece = pieces[i]; 
        
                    // Connect this piece to their north, south, east, and west 
                    // neighbors (if they exist). 
                    if (i >= 3) 
                        piece.expectedConnections.push(pieces[i-3]); // N
                    if (i < 6) 
                        piece.expectedConnections.push(pieces[i+3]); // S
                    if (i % 3 < 2) 
                        piece.expectedConnections.push(pieces[i+1]); // E
                    if (i%3 > 0) 
                        piece.expectedConnections.push(pieces[i-1]); // W
                }
                gameState = GameState.Stalling; 
                stateTime = timeSeconds();
            });
        }
    
        var img = new Image(); 
        img.onload = whenLoad; 
        img.onerror = function() { 
            alert("Error loading image " + this.puzzleFileName); 
        } 
        img.src = this.puzzleFileName; 
    
        var stencils = [];
        for (let i = 1; i <= 9; i++) {
            var imgStencil = new Image();
            imgStencil.onload = whenLoad; 
            let fname = this.stencilFolderName + i + ".jpg"; 
            imgStencil.onerror = function() { 
                alert("Error loading images " + fname); }
            imgStencil.src = fname;
            stencils.push(imgStencil); 
        }
    }

    // Loads the assets for this puzzle.
    load() {
        this.initializeLevel(); 
        gameCanvas.canvas.style.backgroundColor = this.backgroundColor;
    }
}
