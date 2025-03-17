// import FadingChar from "@/components/FadingChar";
import { useEffect } from "react";
// import { createRoot } from 'react-dom/client';
import "./animation.css";


function Animation() {
    // on mount append a bunch of FadingChars to the div
const paragraph = `
    Whispers of the Evernight

Beneath the endless dome
A silver river winds its
It murmurs softly from
As night breathes in 
The world spins on, 
A tale of old, both 

The moon, a ghost of quiet grace,
Spills light upon the emerald trees,
And shadows twist in secret space,
Dancing with a gentle breeze.
The wind, a whisper from the past,
Carries secrets, meant to last.

In fields of gold, where dreams are sown,
The flowers bloom with colors bright,
And in their petals, truths are known,
Invisible to the waking light.
They speak of days that slip away,
Of whispered nights that long to stay.

The mountains rise, majestic, tall,
Their peaks like whispers, soft and deep,
They watch the world beneath them fall,
And in their gaze, the earth does sleep.
With every stone and every breath,
They stand as witnesses to death.

But life, it rises in the dark,
As stars are born from endless space,
Each moment holds a secret spark,
A fleeting, soft, eternal trace.
The fire in our hearts, so bright,
Is fed by shadows, kissed by light.

The ocean, vast, its waters speak,
Of journeys long and ships now gone,
Yet still it roars, both strong and meek,
With whispers deep that carry on.
Beneath its waves, a world does spin,
A tale of life, both thick and thin.

And on this earth, so wild, so free,
We walk the path, both lost and found,
Searching for what we cannot see,
Yet knowing well it’s all around.
The sky above, the soil below,
All things in silence come and go.

In every footstep, a memory,
In every breath, a silent prayer,
The world spins on in harmony,
And still we seek, though unaware.
The sun will rise, the moon will fade,

`



function createFadingChar(char: string): HTMLElement {
    const longListofRandomCharacters = "abcdefghijklmnopqrstuvwxyzlasidkbnASDV9083457458T8YQRO0IPGBN GF";
    
    const getRandomText = () => {
        return longListofRandomCharacters[Math.floor(Math.random() * longListofRandomCharacters.length)];
    };

    const span = document.createElement('span');
    span.className = "container1 w-full h-full";

    const outerDiv = document.createElement('div');
    outerDiv.className = "contrast-button container1 text-white";
    outerDiv.style.fontFamily = "JetBrains Mono, Consolas, monospace";

    const hidingDiv = document.createElement('div');
    hidingDiv.className = "hiding icon text-5xl";
    hidingDiv.innerText = getRandomText();

    const showingDiv = document.createElement('div');
    showingDiv.className = "showing icon text-5xl";
    showingDiv.innerText = char;

    outerDiv.appendChild(hidingDiv);
    outerDiv.appendChild(showingDiv);
    span.appendChild(outerDiv);

    return span;
}


    
    useEffect(() => {
        //creade fadin chars div
        
        const appendDivs = async () => {
            const div = document.createElement('div');
            div.id = "fading-chars";
            div.className = " w-full bg-white mx-auto p-4 char-container text-black text-5xl";
            div.style.fontFamily = "JetBrains Mono, Consolas, monospace";
            let paragraphTrimmed = paragraph.trim();
            let lines = paragraphTrimmed.split("\n");
            

            

            
            //append to MAIN div
            const mainDiv = document.querySelector("main");
            // make main background white
            if (mainDiv) {
                mainDiv.classList.add("bg-white");
                mainDiv.appendChild(div);
            }
            for (let i = 0; i < lines.length; i++) {
                let line = lines[i];
                let lineArray = line.trim().split("");
                lineArray.push("\n");
                console.log(lineArray[lineArray.length - 1], lineArray[lineArray.length - 1] === "\n");
                for (let j = 0; j < lineArray.length; j++) {
                    // console.log("is line break", lineArray[j] === "\n");
                    if (lineArray[j] === "\n") {
                        const br = document.createElement("br");
                        div?.appendChild(br);
                    } else {
                        const span = createFadingChar(lineArray[j]);
                        div?.appendChild(span);

                        setTimeout(() => {
                            let innerString = span.querySelector(".showing")?.textContent;
                            //if it's a space replace with html space
                            if (innerString) {
                                span.replaceWith(innerString);
                            }

                        }, 400);
                    }
                    await new Promise(resolve => setTimeout(resolve, 1));
                }

                // console.log(paragraphArray[i]);
               
                


            }
        };
        appendDivs();
    }, []);


  return (
    <div >
    {/* // id="fading-chars"
    // className="flex flex-row flex-wrap w-full bg-white mx-auto p-4 char-container" */}
    </div>
  );
}

export default Animation;
