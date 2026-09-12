package main

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"
)

func run(dir string, args ...string) {
	cmd := exec.Command(args[0], args[1:]...)
	cmd.Dir = dir
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		os.Exit(1)
	}
}

// parseCommands extracts the shell commands from a .trident.yml file: a flat
// YAML list of scalar strings, one "- command" per line, in order.
func parseCommands(r io.Reader) []string {
	var commands []string
	scanner := bufio.NewScanner(r)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if !strings.HasPrefix(line, "- ") {
			continue
		}
		commands = append(commands, strings.TrimPrefix(line, "- "))
	}
	return commands
}

func main() {
	repo := os.Args[1]
	commit := os.Args[2]

	run("", "git", "clone", repo, "repo")
	run("repo", "git", "checkout", commit)

	if f, err := os.Open("repo/.trident.yml"); err == nil {
		defer f.Close()
		for _, cmd := range parseCommands(f) {
			fmt.Printf("+ %s\n", cmd)
			run("repo", "sh", "-c", cmd)
		}
	}

	fmt.Println("done")
}
