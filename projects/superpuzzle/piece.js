// Now we need to factor in the magnetic attraction/repulsion of 
// pieces. This function determines the vector [fx, fy] that is the 
// force (in distance) of either attraction (if (from) wants to go 
// towards (to)) or repulsion (if (from) wants to go away from (to)).
function force(from, to) {
    // Determine if (from) wants to connect to (to). Determined by if 
    // our piece chain wants to connect with their piece chain. 
    let rootFrom = from; // from.findRoot();
    let rootTo = to; // to.findRoot(); 

    // If we're attracted to the other piece, then we must be attracted to the
    // point the other piece wants us to connect to. If it exists, this is
    // that location. TODO  
    let [ex, ey] = [0, 0]; 

    // Is there at least one node in (rootFrom) which is attracted to 
    // at least one node in (rootTo)? 
    let factor = 0; 
    let stackFrom = [rootFrom]; 
    while (stackFrom.length > 0) {
        let itemFrom = stackFrom.pop(); 
        let stackTo = [rootTo];
        while (stackTo.length > 0) {
            let itemTo = stackTo.pop(); 
            if (itemFrom == itemTo) {
                // Either we're determining the force of ourselves, 
                // or we're finding the force between ourselves and 
                // a puzzle piece already connected to ourselves. 
                return [0, 0];
            }
            else if (itemFrom.expectedConnections.includes(itemTo)) {
                // The pieces want to be connected to each other. 
                factor = -1;
                break; 
            }

            for (let i = 0; i < itemTo.children.length; i++) 
                stackTo.push(itemTo.children[i]);
        }

        if (factor == -1) {
            // We can be sure there are no other sources of attraction or 
            // repulsion that matter. 
            break; 
        } 

        for (let i = 0; i < itemFrom.children.length; i++) 
            stackFrom.push(itemFrom.children[i]); 
    }

    if (factor != -1) {
        // We must be repulsed because we can't locate one puzzle piece which
        // is attracted. 
        factor = 1; 
    }

    if (isNaN(to.px) || isNaN(to.py)) 
        return [0, 0]; // Probably uninitialized or out of bounds, ignore.

    // Direction of attraction/repulsion is just the direction to the piece. 
    let dx = (to.px - from.px) + (to.cx - from.cx); 
    let dy = (to.py - from.py) + (to.cy - from.cy); 
    if (dx == 0) dx = 0.001; 
    if (dy == 0) dy = 0.001; 
    let mag = Math.sqrt(Math.pow(dx, 2) + Math.pow(dy, 2)); 
    
    // Equation: distance = 0 -> force = 100, distance = 500 -> force = 0. 
    let forceMax = 100; 
    let distMax = 500; 
    let fx = factor * (-(distMax / forceMax) * dx + forceMax); // (1 / dx); 
    let fy = factor * (-(distMax / forceMax) * dy + forceMax); // (1 / dy);
    return [fx, fy]; // TODO don't make magnitude linear.
}

class Piece {
    static MovementType = Object.freeze({
        Gravity: Symbol("gravity"), 
        Still: Symbol("still"),
        Needle: Symbol("needle"),
        Taffy: Symbol("taffy"), 
        Circular: Symbol("circular"), 
        Blink: Symbol("blink"), 
        Wrap: Symbol("wrap"), 
        Fling: Symbol("fling") 
    });

    // Creates a new puzzle piece from the given bitmap image. The piece is 
    // centered at (cx, cy) within the bitmap image. It also is located at 
    // (px, py) within the global canvas, with the top-left of the bitmap as
    // the anchor point. The piece itself has size defined by (width, height). 
    // A list of expected connections is created but not implemented; it's up
    // to the calling function to do this after all pieces have been created.
    constructor(bitmap, row, col, px, py, width, height, movementType) {
        this.bitmap = bitmap; 
        this.row = row; 
        this.col = col; 
        this.cx = col * width + width / 2; 
        this.cy = row * height + height / 2; 
        this.px = px; 
        this.py = py; 
        this.width = width; 
        this.height = height; 

        // This must be filled out by the calling process. 
        this.expectedConnections = []; 
        this.children = []; 
        this.parent = null; 
        this.count = 1; 

        // Extents of this node. This is more interesting if we have children, 
        // but at initialization we don't. 
        let [left, right, top, bottom] = this.getTreeExtents();
        this.left = left; 
        this.right = right; 
        this.top = top; 
        this.bottom = bottom;
        
        // Focused pieces are being held by the player, and they should not 
        // connect to things automatically. 
        this.isFocused = false;

        // The way the puzzle piece will move inside of its update() function.
        this.movementType = movementType;
        this.generateVelocity();
    }

    // Creates the initial velocity for this piece given its movement type.
    generateVelocity() {
        if (this.movementType == Piece.MovementType.Gravity) {
            this.vx = (Math.random() - 0.5) * 100; 
            this.vy = (Math.random() - 0.5) * 100;
        }
        else if (this.movementType == Piece.MovementType.Still) {
            this.vx = 0; 
            this.vy = 0; 
        }
        else if (this.movementType == Piece.MovementType.Needle) {
            let rads = Math.random() * Math.PI * 2; 
            const mag = 200;
            this.vx = Math.sin(rads) * mag;
            this.vy = Math.cos(rads) * mag; 
        }
        else if (this.movementType == Piece.MovementType.Taffy) {
            this.vx = 0; 
            this.vy = 600 * (Math.random() > 0.5 ? 1 : -1);
        }
        else if (this.movementType == Piece.MovementType.Circular) {
            this.rads = Math.random() * Math.PI * 2;
            this.vr = Math.PI * 2; // Radians per second.
            this.vel = 400; // Velocity in the direction of the angle. 
        }
        else if (this.movementType == Piece.MovementType.Blink) {
            this.vx = 0; 
            this.vy = 0;
            this.frequency = 3; // How many seconds before moving.
            this.lastSwitch = 0; // The time the program was at last move.
        }
        else if (this.movementType == Piece.MovementType.Wrap) {
            this.vx = 400 / this.count; 
            this.vy = 0; 
        }
    }

    // Gets the extents [left, right, top, bottom] of this single node in 
    // relation to (px, py).
    getExtents() {
        return [
            this.cx - this.width / 2, 
            this.cx + this.width / 2, 
            this.cy - this.height / 2, 
            this.cy + this.height / 2
        ];
    }

    // In relation to (px, py), this returns the offset [left, right, top, 
    // bottom] of our extents considering our children pieces. This should be 
    // re-calculated each time a new child is added. This should only be 
    // calculated for the root node, as the root node is the only node with 
    // complete access to the extents. 
    getTreeExtents() {
        // Find the left-most, right-most, top-most, and bottom-most child.
        let leftMost = canvasWidth; 
        let rightMost = 0; 
        let topMost = canvasHeight; 
        let bottomMost = 0; 

        let stack = [this]; 
        while (stack.length > 0) {
            let item = stack.pop(); 

            // Calculate the extents only for the current node and compare it 
            // to the given values.
            const [left, right, top, bottom] = item.getExtents(); 
            if (left < leftMost) leftMost = left; 
            if (right > rightMost) rightMost = right; 
            if (top < topMost) topMost = top; 
            if (bottom > bottomMost) bottomMost = bottom; 
            
            for (let i = 0; i < item.children.length; i++) 
                stack.push(item.children[i]); 
        }
        
        return [leftMost, rightMost, topMost, bottomMost]; 
    }

    // Draws the puzzle piece to the screen (defined by the context). 
    draw(ctx) { 
        let stack = [this]; 
        while (stack.length > 0) {
            let item = stack.pop(); 
            ctx.drawImage(item.bitmap, this.px, this.py); 
            for (let i = 0; i < item.children.length; i++) 
                stack.push(item.children[i]); 
        }
        
        // Drawing it as a stack vs. with recursion may help resolve a visual
        // issue with pieces not appearing connected. 
        /*
        ctx.drawImage(this.bitmap, this.px, this.py); 
        for (let i = 0; i < this.children.length; i++) 
            this.children[i].draw(ctx); 
        */
    }

    // Returns true if (x, y) overlaps with this specific puzzle piece, false
    // otherwise. 
    isOverlap(x, y) {
        for (let i = 0; i < this.children.length; i++) 
            if (this.children[i].isOverlap(x, y))
                return true;
        
        // Get the extents of this single piece and compare them to the mouse,
        // considering how the extents are defined in relation to (px, py). 
        x -= this.px; 
        y -= this.py; 
        const [left, right, top, bottom] = this.getExtents(); 

        return x > left && x < right && y > top && y < bottom; 
        
        // return (Math.abs(x - this.px - this.cx) < this.width / 2 &&
        //    Math.abs(y - this.py - this.cy) < this.height / 2); 
    }

    // Checks each of the pieces this piece is capable of connecting with, 
    // and returns one specific piece it can currently connect with (if it 
    // exists). We may check our children to see if they can connect with some
    // other piece. If they can, we'll call ourselves recursively. A tuple is 
    // returned denoting the piece we can connect with and the piece (either
    // ourself or one of our children) that does the connecting with the new
    // piece. 
    canConnect() {
        // Check if we can connect with any of our own neighbors. 
        for (let i = 0; i < this.expectedConnections.length; i++) {
            let other = this.expectedConnections[i]; 

            // Make sure the expected direction is almost parallel.
            let edx = other.col - this.col;
            let edy = other.row - this.row;
            let diffx = (other.px - this.px) + (other.cx - this.cx);
            let diffy = (other.py - this.py) + (other.cy - this.cy);
            let dot = (edx * diffx) + (edy * diffy);
            let almostParallel = 1 - dot < 0.25; 

            // Make sure the distance is almost right next to each other. 
            let diffDist = Math.sqrt(Math.pow(diffx, 2) + Math.pow(diffy, 2)); 
            let almostNext = Math.abs(this.width - diffDist) < this.width / 4;
            
            if (almostParallel && almostNext)
                return [this, other]; 
        }

        // Do the same for each of our children. 
        for (let i = 0; i < this.children.length; i++) { 
            let [from, to] = this.children[i].canConnect();
            if (to != null)
                return [from, to]; 
        }

        return [null, null]; 
    }

    // Attempts to connect this node to another. This should only be called 
    // on a root node.
    attemptConnect() {
        if (this.parent != null) 
            throw new Error("attemptConnect called on non-root.");
        
        // Attempt to connect this piece with another. 
        let [fromPiece, toPiece] = this.canConnect(); 
        if (toPiece != null) { 
            // A connection is successful. Remove the connected piece from the 
            // pieces array and add it as a child of this piece.
            let idx = pieces.indexOf(toPiece); 
            if (idx != -1) {
                pieces.splice(idx, 1);
                fromPiece.connect(toPiece);
            } 
            else { 
                toPiece.connect(fromPiece);
                // The piece we're trying to connect to is the child of 
                // another piece. To make things simpler, lets say that we're 
                // the child of them (instead of they're the child of us). 
                // Otherwise, we have a piece which has multiple parents.
                let idx = pieces.indexOf(fromPiece); 
                if (idx != -1) {
                    // The pieces array may possibly not contain the fromPiece.
                    // It's required a root to call this attemptConnect
                    // function, but fromPiece may not equal the same piece 
                    // that called this function.
                    pieces.splice(idx, 1); 
                }
                else 
                    arrayRemove(pieces, this); // TODO: explain. 
            }
        }
    }
    
    static removeExpected(pieceOne, pieceTwo) {
        let idx = pieceOne.expectedConnections.indexOf(pieceTwo); 
        if (idx != -1) pieceOne.expectedConnections.splice(idx, 1); 

        idx = pieceTwo.expectedConnections.indexOf(pieceOne); 
        if (idx != -1) pieceTwo.expectedConnections.splice(idx, 1); 
    }

    // Returns the root node of this piece. 
    findRoot() {
        let root = this; 
        while (root.parent != null) 
            root = root.parent; 
        return root; 
    } 
    
    // Connects this piece with the parameter. 
    connect(other) {
        // This puzzle piece and the other puzzle piece forms two trees. First
        // we make sure they don't individually consider each other 
        // expectedConnections, since they are now officially connected. 
        Piece.removeExpected(this, other);

        // Now, we find the roots of each tree. 
        let thisRoot = this.findRoot();
        let otherRoot = other.findRoot();

        // Make sure the connected piece has the same position as the root. The
        // group of pieces (connected originally to either (other) or (this)) 
        // that has the largest size will become the basis for the size. 
        let x = 0;
        let y = 0;
        if (thisRoot.count > otherRoot.count) {
            x = thisRoot.px; 
            y = thisRoot.py;
        } 
        else {
            x = otherRoot.px; 
            y = otherRoot.py;
        }

        // Make sure that no node in this tree considers any other node in the
        // other tree to be an expectedConnection, and vice versa.
        let thisStack = [thisRoot]
        while (thisStack.length > 0) {
            let thisItem = thisStack.pop();
            
            // The surrounding while-loop goes through each node in this tree.
            // We want to do the same for each node in the other tree. 
            let otherStack = [otherRoot]; 
            while (otherStack.length > 0) {
                let otherItem = otherStack.pop(); 

                // The surrounding inner while-loop goes through each node in
                // the other tree. We want to make sure that (thisItem) does 
                // not conflict with each (otherItem). 
                Piece.removeExpected(thisItem, otherItem);

                for (let i = 0; i < otherItem.children.length; i++)
                    otherStack.push(otherItem.children[i]); 
            }

            for (let i = 0; i < thisItem.children.length; i++) 
                thisStack.push(thisItem.children[i]); 
        }

        if (other.parent != null) {
            // (other) is not a root node. (this) is also not a root node. In
            // order to connect them, we need to make (other) a root node. We 
            // can do this by making (other) a root node, which is possible if 
            // we flip the direction of every connection between (other) and 
            // (other)'s root. First, we start at (other). 
            let parentNode = null; // Initially, no parent (root).
            let currentNode = other;

            // While we haven't yet reached the root, flip connections. 
            while (currentNode != otherRoot) {
                // Say that (currentNode) is the parent.
                currentNode.children.push(currentNode.parent); 
    
                // (currentNode)'s parent should no longer consider it as 
                // their child.
                arrayRemove(currentNode.parent.children, currentNode);

                // Set currentNode's parent to their new parent (which was 
                // determined in the previous iteration, or null initially).
                let nextIteration = currentNode.parent;
                currentNode.parent = parentNode;
                parentNode = currentNode;
                currentNode = nextIteration;
            }

            // Now connect (this) and (other), knowing that (other) is simply 
            // a root.
            this.children.push(other); 
            other.parent = this; 
        }

        // (other) is guaranteed to be a root node, so we can make it a child 
        // of (this) to allow us to extend ourselves.
        this.children.push(other); 
        other.parent = this;

        // The root of our own tree has gained new extents, so we should 
        // set them.
        let [left, right, top, bottom] = thisRoot.getTreeExtents();
        thisRoot.left = left; 
        thisRoot.right = right; 
        thisRoot.top = top; 
        thisRoot.bottom = bottom;
     
        // Sets the location of each piece with the values we calculated 
        // before.
        let stack = [thisRoot]; 
        while (stack.length > 0) {
            let item = stack.pop(); 
            item.px = x; 
            item.py = y; 
            for (let i = 0; i < item.children.length; i++) 
                stack.push(item.children[i]); 
        }

        // thisRoot has gained a new piece due to the other piece connecting to
        // it, which will impact its mass in force calculations.
        thisRoot.count += otherRoot.count; 
    }
    
    // Moves this piece (and its children) relative to the direction.
    move(dx, dy) {
        this.px += dx; 
        this.py += dy;
        for (let i = 0; i < this.children.length; i++) 
            this.children[i].move(dx, dy); 
    } 

    // Updates this piece. This piece will move slightly.
    update(deltaTime) {
        if (this.isFocused) 
            return;
        
        if (this.movementType == Piece.MovementType.Gravity) {
            // Modify velocity according to the force. Sum the force of this 
            // piece and every other. Note that update will only be called on 
            // root nodes.
            let [sumfx, sumfy] = [0, 0]; 
            for (let i = 0; i < pieces.length; i++) {
                if (pieces[i] != this) {
                    let [fx, fy] = force(this, pieces[i]); 
                    sumfx += fx; 
                    sumfy += fy; 
                }
            }
       
            let ax = Math.sign(sumfx) * Math.min(Math.abs(sumfx), 100);
            let ay = Math.sign(sumfy) * Math.min(Math.abs(sumfy), 100); 
            this.vx += deltaTime * ax / this.count; 
            this.vy += deltaTime * ay / this.count; 

            this.move(this.vx * deltaTime, this.vy * deltaTime);  
        }
        else if (this.movementType == Piece.MovementType.Still) {
            // Do nothing. 
        }
        else if (this.movementType == Piece.MovementType.Needle ||
                 this.movementType == Piece.MovementType.Taffy || 
                 this.movementType == Piece.MovementType.Wrap) {
            this.move(this.vx * deltaTime, this.vy * deltaTime); 
        }
        else if (this.movementType == Piece.MovementType.Fling) {
            // We want to go off of the screen. Our velocity should have 
            // already been set, so we should just travel in that direction. 
            this.vy -= 500 * deltaTime; 
            this.move(this.vx * deltaTime, this.vy * deltaTime); 
        }
        else if (this.movementType == Piece.MovementType.Circular) {
            this.rads += this.vr * deltaTime; 
            let vx = Math.cos(this.rads) * this.vel;
            let vy = Math.sin(this.rads) * this.vel; 
            this.move(vx * deltaTime, vy * deltaTime); 
        }
        else if (this.movementType == Piece.MovementType.Blink) {
            let time = Math.floor(timeSeconds()); 
            if (time - this.lastSwitch > this.frequency) {
                this.lastSwitch = time;

                let width = this.right - this.left; 
                let height = this.bottom - this.top; 
                let newX = Math.random() * (canvasWidth - width) + 
                    width / 2; 
                let newY = Math.random() * (canvasHeight - height) + 
                    height / 2;
                let curX = this.px + this.cx; 
                let curY = this.py + this.cy; 
                this.move(newX - curX, newY - curY); 
            } 
        }

        if (this.movementType == Piece.MovementType.Gravity || 
            this.movementType == Piece.MovementType.Needle || 
            this.movementType == Piece.MovementType.Taffy || 
            this.movementType == Piece.MovementType.Circular) 
        { 
            let dampen = (this.movementType == Piece.MovementType.Gravity) ? 
                0.5 : 1.0;

            let left = this.px + this.left;
            let right = this.px + this.right; 
            let top = this.py + this.top; 
            let bottom = this.py + this.bottom; 
    
            // Stay at the edge of walls.
            if (left < 0) { 
                this.vx = -this.vx * dampen;
                this.move(-left, 0); 
            }
            else if (right > canvasWidth) {
                this.vx = -this.vx * dampen; 
                this.move(canvasWidth - right, 0); 
            } 
            if (top < 0) {
                this.vy = -this.vy * dampen;  
                this.move(0, -top); 
            }
            else if (bottom > canvasHeight) {
                this.vy = -this.vy * dampen; 
                this.move(0, canvasHeight - bottom); 
            }
        }
        else if (this.movementType == Piece.MovementType.Wrap) {
            let left = this.px + this.left; 
            let right = this.px + this.right; 
            let top = this.py + this.top; 
            let bottom = this.py + this.bottom;

            if (right < 0)
                this.move(-right + canvasWidth - 1, 0);  
            else if (left > canvasWidth)
                this.move(-(left - canvasWidth) - canvasWidth - (right - left) + 1, 0); 
            if (top < 0) 
                this.move(0, -top + 1); 
            else if (bottom > canvasHeight)
                this.move(0, -(bottom - canvasHeight) - 1); 
        }
    }
}
