use std::thread;

fn main() {
    let mut counter = 0;
    let mut handles = vec![];

    for _ in 0..10 {
        // BROKEN: 'counter' cannot be moved into multiple threads.
        // Rust's borrow checker will stop this from compiling.
        let handle = thread::spawn(move || {
            counter += 1;
        });
        handles.push(handle);
    }

    for handle in handles {
        handle.join().unwrap();
    }

    println!("Result: {}", counter);
}