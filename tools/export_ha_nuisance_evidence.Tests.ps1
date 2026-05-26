Describe "Get-RedactedMessage" {
    BeforeAll {
        . "$PSScriptRoot/export_ha_nuisance_evidence.ps1"
    }

    It "redacts an access token from a message" {
        Get-RedactedMessage -Message "Bearer abc123 failed" -Token "abc123" |
            Should -Be "Bearer [REDACTED_TOKEN] failed"
    }

    It "redacts every occurrence of the token" {
        Get-RedactedMessage -Message "abc123 then abc123" -Token "abc123" |
            Should -Be "[REDACTED_TOKEN] then [REDACTED_TOKEN]"
    }

    It "returns the original message when token is empty" {
        Get-RedactedMessage -Message "nothing changes" -Token "" |
            Should -Be "nothing changes"
    }

    It "returns the original message when message is empty" {
        Get-RedactedMessage -Message "" -Token "abc123" |
            Should -Be ""
    }

    It "returns null when message is null" {
        Get-RedactedMessage -Message $null -Token "abc123" |
            Should -BeNullOrEmpty
    }

    It "leaves message unchanged when token is not present" {
        Get-RedactedMessage -Message "safe message" -Token "abc123" |
            Should -Be "safe message"
    }

    It "treats token text literally rather than as regex" {
        Get-RedactedMessage -Message "token a.b[c] leaked" -Token "a.b[c]" |
            Should -Be "token [REDACTED_TOKEN] leaked"
    }
}

Describe "Invoke-HAGet" {
    BeforeAll {
        # Dot source but provide dummy parameters to bypass the prompt from top-level param block
        . "$PSScriptRoot/export_ha_nuisance_evidence.ps1" -BaseUrl "dummy" -AccessToken "dummy" -StartDate (Get-Date) -EndDate (Get-Date) -OutputFolder "dummy"
    }

    It "returns Invoke-RestMethod results on success" {
        Mock Invoke-RestMethod {
            [pscustomobject]@{ ok = $true }
        }

        $result = Invoke-HAGet `
            -Uri "http://ha.local/api/states" `
            -Headers @{ Authorization = "Bearer secret-token" } `
            -Token "secret-token"

        $result.ok | Should -Be $true

        Assert-MockCalled Invoke-RestMethod -Times 1 -Exactly -ParameterFilter {
            $Uri -eq "http://ha.local/api/states" -and $Method -eq "Get"
        }
    }

    It "redacts the access token from thrown errors" {
        Mock Invoke-RestMethod {
            throw "Request failed with token secret-token"
        }

        {
            Invoke-HAGet `
                -Uri "http://ha.local/api/states" `
                -Headers @{ Authorization = "Bearer secret-token" } `
                -Token "secret-token"
        } | Should -Throw "*Home Assistant GET failed for 'http://ha.local/api/states'*"

        try {
            Invoke-HAGet `
                -Uri "http://ha.local/api/states" `
                -Headers @{ Authorization = "Bearer secret-token" } `
                -Token "secret-token"
        }
        catch {
            $_.Exception.Message | Should -Match "\[REDACTED_TOKEN\]"
            $_.Exception.Message | Should -Not -Match "secret-token"
        }
    }
}
