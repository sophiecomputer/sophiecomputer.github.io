import { initializeApp } from "https://www.gstatic.com/firebasejs/12.14.0/firebase-app.js";
import { initializeAppCheck, ReCaptchaV3Provider } from "https://www.gstatic.com/firebasejs/12.14.0/firebase-app-check.js";
import { getDatabase, ref, push, get, onValue, update } from "https://www.gstatic.com/firebasejs/12.14.0/firebase-database.js";
import { getAuth, signInAnonymously, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/12.14.0/firebase-auth.js";

// Firebase init. All of this is *public*, so its fine for users to see. 
const firebaseConfig = {
  apiKey: "AIzaSyAkGRdWha5ZfNkIlqLj-wzUyZ-FyTCG7Ns",
  authDomain: "sophiecomputer-8dc5b.firebaseapp.com",
  projectId: "sophiecomputer-8dc5b",
  storageBucket: "sophiecomputer-8dc5b.firebasestorage.app",
  messagingSenderId: "590233660535",
  appId: "1:590233660535:web:6d6dc8c988800e5b2fea72", 
  databaseURL: "https://sophiecomputer-8dc5b-default-rtdb.firebaseio.com"
};
const app = initializeApp(firebaseConfig);

// App Check must be initialized before database or auth are used.
initializeAppCheck(app, {
  provider: new ReCaptchaV3Provider("6LdeSxItAAAAAC6WfS7SaLn8sjP2cCdfDiS0YI9X"),
  isTokenAutoRefreshEnabled: true
});

const database = getDatabase(app);
const auth = getAuth(app);

export function initComments(postId, commentsDiv, summarize) {
  // HTML element references.
  function make(placeholder, div, typ) {
    const p = document.createElement("p");
    const inp = document.createElement(typ);
    inp.setAttribute("type", "text");
    inp.setAttribute("placeholder", placeholder);
    inp.setAttribute("style", "width: 100%;");
    p.appendChild(inp);
    div.appendChild(p); 
    return inp;
  }
  const inputArea = document.createElement("div"); 
  inputArea.setAttribute("class", "main-section");

  const nameInput = make("Input your name...", inputArea, "input");
  const websiteInput = make("Input your website URL (optional)...", inputArea, "input");
  const messageInput = make("Input your message...", inputArea, "textarea"); 
  
  const submitP = document.createElement("p");
  const submitButton = document.createElement("button");
  submitButton.textContent = "Submit Comment";
  submitP.appendChild(submitButton);
  inputArea.appendChild(submitP);
  
  const messagesDisplay = document.createElement("div");
  let superDiv = null;
  let summaryElement = null; 
  if (summarize) {
    // Wrap everything in a "details" block, with the summary being text indicating how many 
    // comments there are.
    const details = document.createElement("details");
    summaryElement = document.createElement("summary");
    summaryElement.textContent = "0 Comments";
    summaryElement.setAttribute("style", "padding-left: 20px; padding-bottom: 10px;"); 
    details.appendChild(summaryElement);
    details.setAttribute("style", "padding-right: 0px;");  
    commentsDiv.appendChild(details);
    inputArea.setAttribute("style", "border: thin solid black; border-width: 1px;"); 
    superDiv = details;
  }
  else {
    // Emit the content directly. 
    superDiv = commentsDiv;
  }
  superDiv.appendChild(inputArea);
  superDiv.appendChild(messagesDisplay); 

  // Authenticate the user. 
  let currentUserId = null;
  submitButton.disabled = true;
  let onlyOnce = true; 
  onAuthStateChanged(auth, async (user) => {
    if (user) {
      currentUserId = user.uid;
      
      try { 
        const metadataRef = ref(database, `user_metadata/${currentUserId}`); 
        const snap = await get(metadataRef); 
        if (!snap.exists()) {
          await update(ref(database), {
            [`user_metadata/${currentUserId}`]: {
              lastCommentTimestamp: 0, 
              commentCount: 0, 
              commentPeriodStart: Date.now()
            }
          }); 
        }
      } catch (error) {
        console.error("User could not authenticate; returning.");
        return; 
      }

      submitButton.disabled = false;
      console.log("User authenticated! " + currentUserId); 

      if (!onlyOnce)
        return;
      onlyOnce = false;
  
      // Submit a new comment.
      submitButton.addEventListener("click", async () => {
        if (!currentUserId) return;
    
        let nameText = nameInput.value.trim();
        let websiteText = websiteInput.value.trim(); 
        let messageText = messageInput.value.trim();
    
        // Sanitize the input text. 
        function sanitize(inputText, length) {
          let text = String(inputText);
          text = text.normalize("NFC"); 
          text = text.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/g, "");  // Replace common control chars. 

          // Enforce character limit.
          if (text.length > length)
             return null;
          return text; 
        }

        const newNameText = sanitize(nameText, 512); 
        if (newNameText == null) {
          alert("Sanitized name exceeds 512 characters, enter a new name. Received: " + nameText);
          return;
        }
        nameText = newNameText; 
        
        const newWebsiteText = sanitize(websiteText, 512);
        if (newWebsiteText == null) {
          alert("Sanitized website exceeds 512 characters, enter a new URL. Received: " + websiteText);
          return;
        }
        websiteText = newWebsiteText; 

        const newMessageText = sanitize(messageText, 1024 * 5); 
        if (newMessageText == null) {
          alert("Sanitized message exceeds 5120 characters, enter a new message. Received: " + messageText);
          return;
        } 
        messageText = newMessageText; 

        if (!nameText) { alert("Please enter a name!"); return; }
        if (!messageText) { alert("Please enter a message!"); return; }
    
        submitButton.disabled = true;
    
        try {
          const metadataRef = ref(database, `user_metadata/${currentUserId}`);
          const metadataSnap = await get(metadataRef);
          const now = Date.now();
    
          // Check rate limit and period client-side before attempting write,
          // so we can show a friendly message. The server enforces this too.
          if (metadataSnap.exists()) {
            const { lastCommentTimestamp, commentCount, commentPeriodStart } = metadataSnap.val();
            const periodExpired = (now - commentPeriodStart) > 604800000; // 7 days
    
            if (!periodExpired) {
              if ((now - lastCommentTimestamp) < 3600000) { // 1 hour
                const minutesLeft = Math.ceil((3600000 - (now - lastCommentTimestamp)) / 60000);
                alert(`Please wait ${minutesLeft} more minute(s) before commenting again.`);
                submitButton.disabled = false;
                return;
              }
              if (commentCount >= 10) {
                const daysLeft = Math.ceil((604800000 - (now - commentPeriodStart)) / 86400000);
                alert(`You've reached the comment limit for this week. Resets in ${daysLeft} day(s).`);
                submitButton.disabled = false;
                return;
              }
            }
          }
    
          // Build the new comment entry.
          const newCommentRef = push(ref(database, `comments/${postId}/${currentUserId}/entries`));
          const newCommentKey = newCommentRef.key;
    
          const isFirstComment = !metadataSnap.exists();
          const existingData = metadataSnap.exists() ? metadataSnap.val() : {};
          const periodExpired = metadataSnap.exists() && (now - existingData.commentPeriodStart) > 604800000;
    
          const newCount = (!metadataSnap.exists() || periodExpired) ? 1 : existingData.commentCount + 1;
          const newPeriodStart = (!metadataSnap.exists() || periodExpired) ? now : existingData.commentPeriodStart;
    
          const updates = {
            [`comments/${postId}/${currentUserId}/entries/${newCommentKey}`]: {
              text: messageText,
              name: nameText,
              url: websiteText, 
              timestamp: now,
              userId: currentUserId
            },
            [`user_metadata/${currentUserId}`]: {
              lastCommentTimestamp: now,
              commentCount: newCount,
              commentPeriodStart: newPeriodStart
            }
          };
    
          await update(ref(database), updates);
    
          nameInput.value = "";
          websiteInput.value = "";
          messageInput.value = "";
          console.log("Submitted comment.");
        } catch (error) {
          if (error.code === "PERMISSION_DENIED") {
            alert("Comment rejected by the server. You may be rate-limited.");
          } else {
            alert("Error submitting comment.");
          }
          console.error(error);
        } finally {
          submitButton.disabled = false;
        }
      });
    
      // Listen to all users' entries by watching the whole comments node.
      onValue(ref(database, `comments/${postId}`), (snapshot) => {
        messagesDisplay.innerHTML = '';
    
        if (!snapshot.exists()) {
          const div = document.createElement("div");
          div.className = "main-section"; 
          if (summarize)
            div.setAttribute("style", "padding-top: 0px; border: thin solid black; border-width: 1px; border-top-width: 0px;");

          const p = document.createElement("p");
          p.textContent = "No comments yet.";
          
          div.appendChild(p);
          messagesDisplay.appendChild(div); 

          return;
        }
      
        // Obtain and sort. 
        const comments = [];
        snapshot.forEach((userSnapshot) => {
          userSnapshot.child("entries").forEach((entrySnapshot) => {
            comments.push(entrySnapshot.val());
          });
        });
        comments.sort((a, b) => b.timestamp - a.timestamp);
        
        comments.forEach((comment) => {
          const div = document.createElement("div");
          div.className = "main-section";
          div.setAttribute("style", "border: thin solid black; border-width: 1px; border-top-width: 0px;"); 
    
          const nameP = document.createElement("p");
          const nameLabel = document.createElement("b");
          nameLabel.textContent = "Name";
          nameP.setAttribute("style", "padding-top: 0px;"); 
          nameP.appendChild(nameLabel);
          nameP.append(": "); 
          
          let url = comment.url;
          if (url.length > 0) { 
            // If the user didn't prepend "https://", append it for them.
            if (!new RegExp("^https?://", "i").test(url)) {
              url = "https://" + url;
            } 

            const link = document.createElement("a");
            link.textContent = comment.name; 
            link.href = url;
            link.target = "_blank"; 
            link.rel = "noopener noreferrer";
            nameP.append(link); 
          }
          else {
            nameP.append(comment.name);
          }
          
          const timestamp = comment.timestamp;
          const comment_date = new Date(timestamp);
          const timestamp_text = comment_date.toLocaleString(); 
          const dateP = document.createElement("p");
          const dateLabel = document.createElement("b");
          dateLabel.textContent = "Date"; 
          dateP.appendChild(dateLabel);
          dateP.append(`: ${timestamp_text}`); 

          const messageP = document.createElement("p");
          const messageLabel = document.createElement("b");
          messageLabel.textContent = "Message";
          messageP.appendChild(messageLabel); 
          messageP.append(`: ${comment.text}`); 

          div.appendChild(nameP);
          div.appendChild(dateP); 
          div.appendChild(messageP); 
          
          messagesDisplay.appendChild(div);
        });
        
        if (summaryElement != null)
          summaryElement.textContent = comments.length + " Comments";
      }, (error) => {
        console.error("Error fetching messages:", error);
      });
    } else {
      currentUserId = null;
      submitButton.disabled = true;
      signInAnonymously(auth);
    }
  });
}
