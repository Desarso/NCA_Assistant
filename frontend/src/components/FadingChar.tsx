import "./animation.css";

function FadingChar({ char }: { char: string }) {
  const longListofRandomCharacters = "abcdefghijklmnopqrstuvwxyzlasidkbnASDV9083457458T8YQRO0IPGBN GF";

  const getRandomText = () => {
    let randomChar =
      longListofRandomCharacters[Math.floor(Math.random() * longListofRandomCharacters.length)];
    return randomChar;
  };

  return (
    <span className="container1 w-full h-full">
      <div
        className="contrast-button container1 text-white"
        style={{ fontFamily: "JetBrains Mono, Consolas, monospace"}}
      >
        <div className={`hiding icon text-5xl`}>{getRandomText()}</div>
        <div className={`showing icon text-5xl`}>{char}</div>
      </div>
    </span>
  );
}

export default FadingChar;
