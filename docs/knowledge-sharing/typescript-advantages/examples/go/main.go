package main

import (
	"encoding/json"
	"fmt"
	"os"
)

func main() {
	data, err := os.ReadFile(os.Args[1])
	if err != nil {
		panic(err)
	}
	var cases []json.RawMessage
	if err := json.Unmarshal(data, &cases); err != nil {
		panic(err)
	}
	for _, raw := range cases {
		out, _ := json.Marshal(parseProduct(raw))
		fmt.Println(string(out))
	}
}
