
// Config variables to be adjusted by each individual website where the script is used
let enableFeedbackButtons = true;
let enableFormatLinks = true;
let minimalistic_design = false;
// botId has to be set explicitely
let botId = "";
let introText = {
    "de":
        "Leerer Begrüßungstext",
    "en":
        "Empty introduction"
};
let locale = "de";

function setup_website() {
    document.getElementById('intro-text').innerHTML = introText[locale];
}

function onMessageDone() {
    // Default do nothing, override as needed
}

// Function pointer to format custom metadata
let customFormatMetadata = null;

let msg_obj = { data: "", botPerformance: "", os: "" }

// Global intern variables

let auto_scroll = false;

let user_id = null;
let botElement = null;
let botMessageContainer = null;
let stop_streaming = false;
let requestId = -1;

let botIsTyping = false;
let botIsTypingElement = null;

let disabledUserInput = false;

let firstMessageSend = false;


// Create the bot typing element
botIsTypingElement = document.createElement("p");
botIsTypingElement.setAttribute("class", "botText");
let typingElement = document.createElement("span");
typingElement.setAttribute("class", "typing-indicator");
typingElement.appendChild(document.createElement("span"));
typingElement.appendChild(document.createElement("span"));
typingElement.appendChild(document.createElement("span"));
botIsTypingElement.appendChild(typingElement);

// Set locale via the flag images
document.getElementById('de-local-flag').addEventListener('click', function () {
    locale = "de"
    document.getElementById('intro-text').innerHTML = introText["de"];

    if (document.getElementById('speedRangeText') != null)
        document.getElementById('speedRangeText').innerHTML = "Geschwindigkeit"
    if (document.getElementById('qualityRangeText') != null)
        document.getElementById('qualityRangeText').innerHTML = "Qualität"

    document.getElementById('sendMessageB').innerHTML = "Senden"
    document.getElementById('stopStreamingB').innerHTML = "Stop"
    if (document.getElementById('sendFeedbackB') !== null)
        document.getElementById('sendFeedbackB').innerHTML = "Feedback senden"
    if (document.getElementById('downloadChatlogB') !== null)
        document.getElementById('downloadChatlogB').innerHTML = "Chatverlauf herunterladen"
    document.getElementById('textInput').placeholder = "Nachricht"

    socket.emit("change_language", { data: { "language": "de" }, botId: botId }, function () {
    });
})
document.getElementById('gb-local-flag').addEventListener('click', function () {
    locale = "en"
    document.getElementById('intro-text').innerHTML = introText["en"];

    if (document.getElementById('speedRangeText') != null)
        document.getElementById('speedRangeText').innerHTML = "Speed"
    if (document.getElementById('qualityRangeText') != null)
        document.getElementById('qualityRangeText').innerHTML = "Quality"

    document.getElementById('sendMessageB').innerHTML = "Send"
    document.getElementById('stopStreamingB').innerHTML = "Stop"
    if (document.getElementById('sendFeedbackB') !== null)
        document.getElementById('sendFeedbackB').innerHTML = "Send feedback"
    if (document.getElementById('downloadChatlogB') !== null)
        document.getElementById('downloadChatlogB').innerHTML = "Download chat-history"
    document.getElementById('textInput').placeholder = "Message"

    socket.emit("change_language", { data: { "language": "en" }, botId: botId }, function () {
    });
})

function disableElement(id, disabled) {
    let ele = document.getElementById(id);
    if (document.getElementById(id) !== null)
        ele.disabled = disabled;
}

function sendUserMessage() {
    let rawText = document.getElementById("textInput").value;
    document.getElementById("textInput").value = "";

    // Abbort sending if the message is empty
    if (rawText.trim() == "")
        return

    // Append the send text
    const ele = document.createElement("p");
    ele.setAttribute("class", "userText");
    const ele2 = document.createElement("span");
    ele2["innerHTML"] = rawText;
    ele.appendChild(ele2);
    document.getElementById("chatbox").appendChild(ele);

    // Activate the bot is typing indicator
    botIsTyping = true;
    document.getElementById("chatbox").appendChild(botIsTypingElement);

    // if (auto_scroll)
    // document.getElementById("sendMessageB").scrollIntoView(false, { behavior: "smooth" });
    // botIsTypingElement.scrollIntoView(false, { behavior: "smooth" });
    document.getElementById("chatbox").scrollIntoView(false, { behavior: "smooth" });

    const formdata = new FormData();
    formdata.append("msg", rawText);
    formdata.append("user_id", user_id);

    document.getElementById("sendMessageB").innerHTML = locale === "de" ? "Warten.." : "Wait..";
    disableElement('sendMessageB', true);
    document.getElementById('textInput').placeholder = locale === "de" ? 'Bitte warten..' : 'Please wait..';
    disableElement('textInput', true);
    disableElement('sendFeedbackB', true);
    disabledUserInput = true;

    send_msg(rawText);
}

document.getElementById('textInput').addEventListener('keydown', function (event) {
    // Send by pressing enter
    if (event.which == 13 && !disabledUserInput) {
        stop_streaming = false;
        sendUserMessage();
    }
})
document.getElementById('sendMessageB').addEventListener('click', function () {
    if (!disabledUserInput) {
        stop_streaming = false;
        sendUserMessage();
        document.getElementById('textInput').focus();
    }
})
document.getElementById('stopStreamingB').addEventListener('click', function () {
    // if (auto_scroll)
    document.getElementById("sendMessageB").scrollIntoView(false, { behavior: "smooth" });

    stop_stream();
})

function updateBotChatMessage(msg, infoMessage = false) {
    if (infoMessage) {
        let botMessageContainer = document.createElement("p");
        botMessageContainer.setAttribute("class", "botText");
        let botElement = document.createElement("p");
        botElement["innerHTML"] = msg;
        botMessageContainer.appendChild(botElement);

        document.getElementById("chatbox").appendChild(botMessageContainer);
    } else {
        if (botElement === null) {
            botMessageContainer = document.createElement("p");
            botMessageContainer.setAttribute("class", "botText");
            botElement = document.createElement("p");
            botElement["innerHTML"] = msg;
            botMessageContainer.appendChild(botElement);

            chatbox = document.getElementById("chatbox");

            chatbox.appendChild(botMessageContainer);
        } else {
            botElement["innerHTML"] = msg

            // Adjust all child elements to prevent overflow out of the botMessageContainer
            let openList = []
            for (let child2 of botElement.children)
                openList.push(child2);
            while (openList.length > 0) {
                let child = openList.shift();
                if (child.tagName === "PRE" || child.tagName === "CODE") {
                    // Break overflowing strings
                    child.style.setProperty('overflow-wrap', "anywhere");
                    // Collapse white-spaces
                    child.style.setProperty('white-space', "pre-line");
                }
                for (let child2 of child.children)
                    openList.push(child2);
            }
        }
    }
}

function showFeedbackButtons() {
    if (enableFeedbackButtons && botMessageContainer !== null) {
        let thumbsUpButton = document.getElementById('thumbsUpButton');
        let thumbsUpButton2 = thumbsUpButton.cloneNode(1);
        thumbsUpButton2.setAttribute("id", "thumbsUpButton_" + requestId);
        thumbsUpButton2.setAttribute("onClick", "(function(){sendFeedback(1, " + requestId + ");})();");
        thumbsUpButton2.classList.remove("hiddenElement");

        let thumbsdDownButton = document.getElementById('thumbsDownButton');
        let thumbsdDownButton2 = thumbsdDownButton.cloneNode(1);
        thumbsdDownButton2.setAttribute("id", "thumbsdDownButton_" + requestId);
        thumbsdDownButton2.setAttribute("onClick", "(function(){sendFeedback(-1, " + requestId + ");})();");
        thumbsdDownButton2.classList.remove("hiddenElement");

        let reportWrongAnswerButton = document.createElement("button");
        reportWrongAnswerButton.setAttribute("id", "reportWrongAnswerButton" + requestId);
        reportWrongAnswerButton.innerHTML = locale == "de" ? "Falsche Antwort melden" : "Report wrong answer";
        reportWrongAnswerButton.setAttribute("class", "feedbackButton");
        reportWrongAnswerButton.setAttribute("style", "vertical-align: top; margin: 0 4px 0 0; height: 29.6px;");
        reportWrongAnswerButton.setAttribute("onClick", "(function(){sendFeedback(\"Wrong Answer\", " + requestId + ");})();");

        let feedbackDiv = document.createElement("div");
        feedbackDiv.setAttribute("class", "feedbackDiv");
        feedbackDiv.appendChild(thumbsUpButton2);
        feedbackDiv.appendChild(thumbsdDownButton2);
        feedbackDiv.appendChild(reportWrongAnswerButton);
        botMessageContainer.appendChild(feedbackDiv);
    }
}

function getOS() {
    let os;
    // userAgentData is only available via HTTPS
    if (typeof navigator.userAgentData !== 'undefined' && navigator.userAgentData != null) {
        os = navigator.userAgentData.platform + ' ' + navigator.userAgentData.mobile;
        // Deprecated but still works for most browsers
    } else if (typeof navigator.platform !== 'undefined') {
        // Android’s navigator.platform is often set as 'linux', so userAgent can be used to circumvent
        if (typeof navigator.userAgent !== 'undefined' && /android/.test(navigator.userAgent.toLowerCase())) {
            os = 'android';
        } else {
            os = navigator.userAgent;
        }
    } else {
        os = 'unknown';
    }

    // Replace all ";" to prevent problems with csv files
    os = os.replace(/;/g, ",");

    // Map both ways of identifiing Android OS to the same result
    if (os == "Android true")
        os = "android"

    return os;
}

function download_chatlog() {
    let chatlog = get_chatlog();
    let filename = "chatlog.json";

    const blob = new Blob([chatlog], { type: 'text/json' });
    if (window.navigator.msSaveOrOpenBlob) {
        window.navigator.msSaveBlob(blob, filename);
    } else {
        const elem = window.document.createElement('a');
        elem.href = window.URL.createObjectURL(blob, { oneTimeOnly: true });
        elem.download = filename;
        elem.style.display = 'none';
        document.body.appendChild(elem);
        elem.click();
        document.body.removeChild(elem);
        window.URL.revokeObjectURL(elem.href);
    }
}

function get_chatlog() {
    let messages = []
    let chatlog = {"date": new Date().toISOString(), "messages": messages};

    for (const child of document.getElementById("chatbox").children) {
        for (const grandchild of child.children) {
            if ((grandchild.tagName === "SPAN" && !grandchild["innerHTML"].startsWith("<span>"))) {
                if (child.classList[0] === "botText") {
                    console.log("Bot: ");
                    // chatlog += "Bot: ";
                    messages.push("Bot: "+grandchild["innerHTML"])
                }
                if (child.classList[0] == "userText") {
                    console.log("User: ");
                    // chatlog += "User: ";
                    messages.push("User: "+grandchild["innerHTML"])
                }
                console.log(grandchild["innerHTML"]);
                // chatlog += grandchild["innerHTML"] + "\n";
            } else if (grandchild.tagName === "P") {
                if (child.classList[0] === "botText") {
                    console.log("Bot: ");
                    console.log(grandchild);
                    console.log(grandchild.children);
                    console.log(grandchild.textContent);
                    // chatlog += "Bot: " + grandchild.textContent + "\n";
                    messages.push("Bot: "+grandchild.textContent)
                }
            }
        }
    }
    console.log("Chatlog:\n\n\n" + JSON.stringify(chatlog))
    return JSON.stringify(chatlog);
}



let socket = io(); // socketio connection to server

socket.on("connect", () => {
    console.log("connected");
});

socket.on("disconnect", () => {
    console.log("disconnected");

    // Has to be reset after a bot message is complete
    botMessageContainer = null;
    botElement = null;

    if (locale === "de") {
        updateBotChatMessage("Verbindung zum Server verloren. Lade die Webseite erneut oder versuche es bitte später nochmal.", true);
    } else {
        updateBotChatMessage("Lost connection to the server. Please reload the website or try is again later.", true);
    }
});

socket.on("send_id", function (msg) {
    let done = msg.done;
    let id = msg.data;
    user_id = id
});

function send_msg(user_msg) {
    let form = document.forms[0];

    if (form !== undefined) {
        let botPerformance = form.elements.botPerformance.value;
        let botPerformanceRange = form.elements.botPerformanceRange.value;
        msg_obj.botPerformance = botPerformanceRange;
    } else {
        msg_obj.botPerformance = 2;
    }

    msg_obj.data = user_msg;
    msg_obj.os = firstMessageSend ? "" : getOS()
    msg_obj.botId = botId

    socket.emit("send_msg", msg_obj, function () {
    });
    firstMessageSend = true;
}
function sendFeedbackText() {
    let rawText = document.getElementById("textInput").value;
    document.getElementById("textInput").value = "";

    // Abbort sending if the message is empty
    if (rawText.trim() == "")
        return

    socket.emit("send_feedback", { data: { "feedback": rawText, "requestId": requestId, "customFeedback": true }, botId: botId }, function () {
    });
}
function sendFeedback(feedback, requestId) {
    let button;
    if (feedback == -1) {
        button = document.getElementById('thumbsdDownButton_' + requestId);

        document.getElementById('thumbsUpButton_' + requestId).hidden = true;
    } else if (feedback == 1) {
        button = document.getElementById('thumbsUpButton_' + requestId);

        document.getElementById('thumbsdDownButton_' + requestId).hidden = true;
    } else {
        button = document.getElementById('reportWrongAnswerButton' + requestId);
        button.innerHTML = locale == "de" ? "Falsche Antwort gemeldet" : "Reported wrong answer"
    }
    button.disabled = true;
    button.classList.add("borderless");

    socket.emit("send_feedback", { data: { "feedback": feedback, "requestId": requestId }, botId: botId }, function () {
    });
}

function stop_stream() {
    stop_streaming = true;
    document.getElementById('textInput').focus();

    if (botIsTyping) {
        chatbox.removeChild(botIsTypingElement);
        botIsTyping = false;
    }

    showFeedbackButtons();
    // Has to be reset after a bot message is complete
    botMessageContainer = null;
    botElement = null;

    updateBotChatMessage(locale === "de" ? "Anfrage abgebrochen." : "Request canceled.", true);

    // Has to be reset again
    botMessageContainer = null;
    botElement = null;

    answer = "";

    requestId = -1;

    console.log("Stop streaming")

    socket.emit("stop_streaming", { data: { "requestId": requestId } }, function () {
    });
}

let answer = "";
socket.on("new_msg", function (msg) {
    // Discard any received messages if streaming has been stopped
    if (stop_streaming) {
        return
    }
    // Ignore the message if it doesn't match with the current id
    if (requestId !== -1 && msg.request_id !== requestId) {
        // console.log("Wrong request_id: " + msg.request_id + " expected ID: " + requestId + " data: " + escape(msg.data))
        // return;
    }

    if (botIsTyping)
        chatbox.removeChild(botIsTypingElement);
    botIsTyping = false;

    let done = msg.done;
    let reply = msg.data;

    requestId = msg.request_id;

    // If the entire data is sent by server
    if (done) {
        let metadata = msg.metadata;

        if (metadata !== null && metadata !== "") {
            // Replace all links with proper html elements
            let answerFormatted = formatLinks(answer) + formatMetadata(metadata);

            updateBotChatMessage(answerFormatted);
        } else {
            updateBotChatMessage(formatLinks(answer));
        }

        stop_streaming = false;
        answer = "";

        showFeedbackButtons();

        // if (auto_scroll)
        if (minimalistic_design) {
            document.getElementById("chatbox").scrollIntoView(false, { behavior: "smooth" });
        } else {
            document.getElementById("sendMessageB").scrollIntoView(false, { behavior: "smooth" });
        }

        // Has to be reset after a bot message is complete
        botMessageContainer = null;
        botElement = null;

        onMessageDone();

    } else {
        // If the answer is still empty, then it is the first reply of the bot
        let isFirstReplyPart = answer.length == 0;

        answer += reply;

        // If the "DOMPurify" script is loaded
        if (typeof DOMPurify !== 'undefined') {
            // answer = DOMPurify.sanitize(answer);
        }

        // Replace all links with proper html elements
        let answerFormatted = formatLinks(answer);

        updateBotChatMessage(answerFormatted);

        if (isFirstReplyPart && auto_scroll) {
            if (minimalistic_design) {
                document.getElementById("chatbox").scrollIntoView(false, { behavior: "smooth" });
            } else {
                document.getElementById("userInput").scrollIntoView(false, { behavior: "smooth" });
            }
        }
    }
});

// Replace all links with proper html elements
function formatLinks(answer) {
    if (enableFormatLinks) {
        // If the "marked" script is loaded
        if (typeof marked !== 'undefined') {
            let m = marked.parse(answer);
            return m;
        }
        // Remove the "[url]" from a markdown url
        answer = answer.replaceAll(/\[(https?:\/\/.)[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)\]/g, '');
        // The [^">] at the beginning is important to not change the previous replaced ones or html generated by formatMetadata()
        answer = answer.replaceAll(/((https?:\/\/.)[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*))/g, '<a target="_blank" href="$1">$1</a>');
        // Replace any "." at the end of the url
        return answer.replaceAll(/\.("|<)/g, '$1');
    } else {
        return answer;
    }
}

function formatMetadata(answer) {
    if (customFormatMetadata !== null) {
        return customFormatMetadata(answer);
    } else {
        let result = "";

        result = "<div class='metadataFlex' style='display: flex;'>";
        result += "<details><summary> " + (locale === "de" ? "Quellen" : "Source") + "</summary>";

        let i = 1;
        for (let m of JSON.parse(answer)) {
            let link = formatLinks(m.source)
            result += "<details><summary> " + (locale === "de" ? "Quelle" : "Source") + "[" + i + "]</summary>" + link + "</details>";
            i++;
        }

        result += "</details>";
        result += "</div>";

        return result;
    }
}

socket.on("request_done", function (msg) {
    if (requestId == -1 || requestId == msg.request_id) {
        document.getElementById("sendMessageB").innerHTML = locale === "de" ? "Senden" : "Send";
        disableElement('sendMessageB', false);
        document.getElementById('textInput').placeholder = locale === "de" ? 'Nachricht' : 'Message';
        disableElement('textInput', false);
        document.getElementById('textInput').focus();
        disableElement('sendFeedbackB', false);
        disabledUserInput = false;
        requestId = -1;
    }
})

socket.on("info", function (msg) {

    if (botIsTyping)
        chatbox.removeChild(botIsTypingElement);

    let done = msg.done;
    let data = msg.data;

    if (data === "#overloaded") {
        if (locale === "de") {
            data = "Der Server ist aktuell überlastet, weshalb es etwas länger dauern kann, deine Anfragen zu bearbeiten. Bitte habe etwas Geduld.";
        } else {
            data = "The server is overloaded at the moment, so your request might take longer to process. Please be patient.";
        }
    }

    updateBotChatMessage(data);

    if (auto_scroll)
        document.getElementById("userInput").scrollIntoView(false, { behavior: "smooth" });

    // Has to be reset after a bot message is complete
    botMessageContainer = null;
    botElement = null;

    if (botIsTyping)
        chatbox.appendChild(botIsTypingElement);
});
