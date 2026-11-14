package main

import "fmt"

func main() {
	res := parseProduct([]byte(`{"id":"p2"}`))
	// Reading Product without checking res.OK compiles, then panics.
	fmt.Println(res.Product.Name)
}
