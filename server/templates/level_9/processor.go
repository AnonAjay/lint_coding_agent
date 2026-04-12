package main

import "fmt"

func main() {
    // BROKEN: An unbuffered channel requires a receiver to be ready 
    // at the exact moment a sender sends.
    ch := make(chan int)

    ch <- 42 // Execution stops here forever!

    val := <-ch
    fmt.Println("Received:", val)
}