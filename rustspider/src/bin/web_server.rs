#[cfg(feature = "web")]
#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let mut host = String::from("0.0.0.0");
    let mut port: u16 = 9090;

    let args: Vec<String> = std::env::args().collect();
    let mut index = 1;
    while index < args.len() {
        match args[index].as_str() {
            "--host" if index + 1 < args.len() => {
                host = args[index + 1].clone();
                index += 1;
            }
            "--port" if index + 1 < args.len() => {
                if let Ok(value) = args[index + 1].parse::<u16>() {
                    port = value;
                }
                index += 1;
            }
            _ => {}
        }
        index += 1;
    }

    rustspider::web::run_server(&host, port).await
}

#[cfg(not(feature = "web"))]
fn main() {
    eprintln!("rustspider web server requires the `web` feature");
    std::process::exit(1);
}
